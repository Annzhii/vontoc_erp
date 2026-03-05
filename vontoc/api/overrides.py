import frappe
from frappe import _
from erpnext.stock.doctype.shipment.shipment import Shipment
from erpnext.stock.doctype.material_request.material_request import MaterialRequest
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt import SubcontractingReceipt
from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import SubcontractingOrder
from erpnext.stock.doctype.item.item import Item
from erpnext.buying.doctype.supplier_quotation.supplier_quotation import SupplierQuotation
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

from vontoc.vontoc.doctype.guideline_price.guideline_price import GuidelinePrice, submit_guideline_price
from frappe.utils import flt, strip_html, cstr
from frappe.desk.doctype.notification_log.notification_log import (enqueue_create_notification)
from erpnext.buying.utils import validate_for_items
from erpnext.manufacturing.doctype.blanket_order.blanket_order import (validate_against_blanket_order)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (validate_inter_company_party, update_linked_doc)

from vontoc.api.purchase_receipt import stock_purchase_receipt, mirror_internal_pr
from vontoc.api.subcontracting_receipt import stock_subcontracting_receipt
from vontoc.api.subcontracting_order import subcontracting_order_submitted
from vontoc.api.purchase_order import approve_po
from vontoc.api.material_request import material_request_submitted
from vontoc.api.sales_order import sales_order_submitted

from vontoc.api.item import validate_sales_temporary_item
from vontoc.api.shipment import check_delivery_notes_submitted
from vontoc.api.sales_invoice import sync_sales_invoice_to_delivery_note, check_allocated_amount
from vontoc.api.delivery_note import check_allow_shipment

class VONTOCPurchaseOrder(PurchaseOrder):
	def on_submit(self):
		super().on_submit()
		approve_po(self)

class VONTOCPurchaseReceipt(PurchaseReceipt):
	def on_submit(self):
		super().on_submit()
		# ✅ 追加你的自定义逻辑
		stock_purchase_receipt(self.name)
		mirror_internal_pr(self)

class VONTOCMaterialRequest(MaterialRequest):
	def on_submit(self):
		self.update_requested_qty_in_production_plan()
		self.update_requested_qty()
		if self.material_request_type == "Purchase":
			self.update_prevdoc_status()
			if frappe.db.exists("Budget", {"applicable_on_material_request": 1, "docstatus": 1}):
				self.validate_budget()
				
		material_request_submitted(self)

class VONTOCSubcontractingReceipt(SubcontractingReceipt):
	def on_submit(self):
		super().on_submit()
		#自定义逻辑
		stock_subcontracting_receipt(self.name)

class VONTOCSubcontractingOrder(SubcontractingOrder):
	def validate(self):
		super().validate()
		self.validate_purchase_order_for_subcontracting()
		self.validate_items()
		self.validate_service_items()
		#允许供应商仓库作为收货仓库
		#self.validate_supplied_items()
		self.set_missing_values()
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

class VONTOCItem(Item):
	def validate(self):
		if not self.item_name:
			self.item_name = self.item_code

		if not strip_html(cstr(self.description)).strip():
			self.description = self.item_name

		self.validate_uom()
		self.validate_description()
		self.add_default_uom_in_conversion_factor_table()
		self.validate_conversion_factor()
		self.validate_item_type()
		self.validate_naming_series()
		self.check_for_active_boms()
		self.fill_customer_code()
		self.check_item_tax()
		self.validate_barcode()
		self.validate_warehouse_for_reorder()
		self.update_bom_item_desc()

		self.validate_has_variants()
		self.validate_attributes_in_variants()
		self.validate_stock_exists_for_template_item()
		self.validate_attributes()
		self.validate_variant_attributes()
		self.validate_variant_based_on_change()
		self.validate_fixed_asset()
		self.clear_retain_sample()
		self.validate_retain_sample()
		self.validate_uom_conversion_factor()
		self.validate_customer_provided_part()
		self.update_defaults_from_item_group()
		self.validate_item_defaults()
		self.validate_auto_reorder_enabled_in_stock_settings()
		self.cant_change()
		self.validate_item_tax_net_rate_range()

		if not self.is_new():
			self.old_item_group = frappe.db.get_value(self.doctype, self.name, "item_group")
		#自定义逻辑
		validate_sales_temporary_item(self)

class VONTOCSupplierQuotation(SupplierQuotation):
    def after_insert(self):
        rfq_names = list(set([
            item.request_for_quotation
            for item in self.items if item.request_for_quotation
        ]))

        if not rfq_names:
            return

        for rfq_name in rfq_names:
            rfq = frappe.get_doc("Request for Quotation", rfq_name)
            users_to_notify = set()
            if rfq.owner:
                users_to_notify.add(rfq.owner)

            if rfq.docstatus == 1 and rfq.modified_by:
                users_to_notify.add(rfq.modified_by)

            users_to_notify = list(users_to_notify)

            if not users_to_notify:
                continue

            # 构建系统通知内容
            notification_doc = {
                "subject": f"收到供应商报价 {self.supplier}",
                "email_content": (
                    f"Supplier Quotation <b>{self.name}</b> has been created "
                    f"for your RFQ <b>{rfq_name}</b>."
                ),
                "document_type": "Supplier Quotation",
                "document_name": self.name,
                "type": "Alert",
            }

            enqueue_create_notification(users_to_notify, notification_doc)

class VONTOCGuidelinePrice(GuidelinePrice):
	def on_submit(self):
		submit_guideline_price(self)

class VONTOCShipment(Shipment):
	def validate(self):
		self.validate_weight()
		self.validate_pickup_time()
		self.set_value_of_goods()
		self.set_total_weight()
		if self.docstatus == 0:
			self.status = "Draft"
		#自定义
		if self.workflow_state == "Ready For Dispatch":
			check_delivery_notes_submitted(self)

class VONTOCSalesInvoice(SalesInvoice):
	def on_update_after_submit(self):
		check_allocated_amount(self)
		sync_sales_invoice_to_delivery_note(self)

class VONTOCDeliveryNote(DeliveryNote):
	def on_submit(self):
		super().on_submit()
		check_allow_shipment(self)

class VONTOCSalesOrder(SalesOrder):
	def on_submit(self):
		super().on_submit()
		sales_order_submitted(self)

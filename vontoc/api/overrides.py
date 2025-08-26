import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import RequestforQuotation
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from frappe.utils import flt, cint
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from erpnext.buying.utils import validate_for_items
from erpnext.manufacturing.doctype.blanket_order.blanket_order import (
	validate_against_blanket_order,
)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	validate_inter_company_party,
)
from vontoc.utils.utils import get_received_qty, is_linked_po_fully_billed
from frappe import _
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	update_linked_doc,
)
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_entry
from vontoc.api.purchase_receipt import create_new_pr_for_shortfall, create_purchase_invoice_from_pr
from vontoc.api.purchase_order import create_invoice_or_receipt_based_on_terms, check_payment_schedule
from vontoc.api.payment_entry import payment_entry_verified
from vontoc.api.request_for_quotation import check_supplier
from vontoc.api.sales_order import create_sales_invoice_or_payment_request
from vontoc.api.sales_invoice import sales_invoice_submitted
from vontoc.api.purchase_invoice import submmit_pi
from vontoc.api.payment_request import payment_request_submitted
from vontoc.api.delivery_note import delivery_note_submitted
from erpnext.setup.doctype.company.company import update_company_current_month_sales

class VONTOCPaymentEntry(PaymentEntry):
	def validate(self):
		self.setup_party_account_field()
		self.set_missing_values()
		self.set_liability_account()
		self.set_missing_ref_details(force=True)
		self.validate_payment_type()
		self.validate_party_details()
		self.set_exchange_rate()
		self.validate_mandatory()
		self.validate_reference_documents()
		self.set_amounts()
		self.validate_amounts()
		self.apply_taxes()
		self.set_amounts_after_tax()
		self.clear_unallocated_reference_document_rows()
		#Save的时候Cheque/Reference No字段非必填
		#self.validate_transaction_reference()
		self.set_title()
		self.set_remarks()
		self.validate_duplicate_entry()
		self.validate_payment_type_with_outstanding()
		self.validate_allocated_amount()
		self.validate_paid_invoices()
		self.ensure_supplier_is_not_blocked()
		self.set_tax_withholding()
		self.set_status()
		self.set_total_in_words()

class VONTOCPurchaseOrder(PurchaseOrder):
	def validate(self):
		#super().validate()
		if self.docstatus == 1 and not self.supplier:
			frappe.throw(_("Supplier is mandatory before submitting the Purchase Order"))
		self.set_status()

		# apply tax withholding only if checked and applicable
		self.set_tax_withholding()

		self.validate_supplier()
		self.validate_schedule_date()
		validate_for_items(self)
		self.check_on_hold_or_closed_status()

		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "stock_qty")

		self.validate_with_previous_doc()
		self.validate_for_subcontracting()
		self.validate_minimum_order_qty()
		validate_against_blanket_order(self)

		if self.is_old_subcontracting_flow:
			self.validate_bom_for_subcontracting_items()
			self.create_raw_materials_supplied()

		self.validate_fg_item_for_subcontracting()
		self.set_received_qty_for_drop_ship_items()
		validate_inter_company_party(
			self.doctype, self.supplier, self.company, self.inter_company_order_reference
		)
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def on_submit(self):
		super().on_submit()

		if self.is_against_so():
			self.update_status_updater()

		self.update_prevdoc_status()
		if not self.is_subcontracted or self.is_old_subcontracting_flow:
			self.update_requested_qty()

		self.update_ordered_qty()
		self.validate_budget()
		self.update_reserved_qty_for_subcontract()

		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total
		)

		self.update_blanket_order()

		update_linked_doc(self.doctype, self.name, self.inter_company_order_reference)

		self.auto_create_subcontracting_order()

		#额外添加的流程逻辑，在approve之后（即表单提交之后）
		create_invoice_or_receipt_based_on_terms(self)
		check_payment_schedule(self)

class VONTOCPurchaseReceipt(PurchaseReceipt):
	def on_submit(self):
		super().on_submit()

		# 保留原始逻辑
		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total
		)

		self.update_prevdoc_status()
		if flt(self.per_billed) < 100:
			self.update_billing_status()
		else:
			self.db_set("status", "Completed")

		self.make_bundle_for_sales_purchase_return()
		self.make_bundle_using_old_serial_batch_fields()
		self.update_stock_ledger()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()
		self.set_consumed_qty_in_subcontract_order()
		self.reserve_stock_for_sales_order()

		# ✅ 追加你的自定义逻辑
		def get_po_item_qty(po_name, item_code):
			if not po_name:
				return 0
			po = frappe.get_doc("Purchase Order", po_name)
			for item in po.items:
				if item.item_code == item_code:
					return item.qty
			return 0

		def function_c(pr_name):
			frappe.msgprint(f"{pr_name}：已收货并付款结清。无需进一步操作。")

		has_shortfall = False
		shortfall_items = []

		for item in self.items:
			po_qty = get_po_item_qty(item.purchase_order, item.item_code)
			received_qty = get_received_qty(item.purchase_order, item.item_code)

			if flt(received_qty) < flt(po_qty):
				shortfall = flt(po_qty) - flt(received_qty)
				shortfall_items.append({
					"item_code": item.item_code,
					"qty": shortfall,
					"po": item.purchase_order,
					"rfq": item.material_request
				})
				has_shortfall = True

		if has_shortfall:
			create_new_pr_for_shortfall(self, shortfall_items)
		elif not is_linked_po_fully_billed(self):
			create_purchase_invoice_from_pr(self)
		else:
			# 调用函数 C
			function_c(self.name)

class VONTOCPurchaseInvoice(PurchaseInvoice):
	def on_submit(self):
		#super().on_submit()
		
		self.check_prev_docstatus()

		if self.is_return and not self.update_billed_amount_in_purchase_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()

		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total
		)

		if not self.is_return:
			self.update_against_document_in_jv()
			self.update_billing_status_for_zero_amount_refdoc("Purchase Receipt")
			self.update_billing_status_for_zero_amount_refdoc("Purchase Order")

		self.update_billing_status_in_pr()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		if self.update_stock == 1:
			self.make_bundle_for_sales_purchase_return()
			self.make_bundle_using_old_serial_batch_fields()
			self.update_stock_ledger()

			if self.is_old_subcontracting_flow:
				self.set_consumed_qty_in_subcontract_order()

		# this sequence because outstanding may get -negative
		self.make_gl_entries()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()

		if frappe.db.get_single_value("Buying Settings", "project_update_frequency") == "Each Transaction":
			self.update_project()

		update_linked_doc(self.doctype, self.name, self.inter_company_invoice_reference)
		self.update_advance_tax_references()

		self.process_common_party_accounting()

		submmit_pi(self)

class VONTOCPaymentRequest(PaymentRequest):
	def on_submit(self):
		if self.payment_request_type == "Outward":
			self.db_set("status", "Initiated")
		elif self.payment_request_type == "Inward":
			self.db_set("status", "Requested")

		'''原有on_submit部分自带逻辑
		send_mail = self.payment_gateway_validation() if self.payment_gateway else None
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)

		if (
			hasattr(ref_doc, "order_type") and ref_doc.order_type == "Shopping Cart"
		) or self.flags.mute_email:
			send_mail = False

		if send_mail and self.payment_channel != "Phone":
			self.set_payment_request_url()
			self.send_email()
			self.make_communication_entry()

		elif self.payment_channel == "Phone":
			self.request_phone_payment()'''
		payment_request_submitted(self)

class VONTOCPaymentEntry(PaymentEntry):
	def on_submit(self):
		if self.difference_amount:
			frappe.throw(_("Difference Amount must be zero"))
		self.make_gl_entries()
		self.update_outstanding_amounts()
		self.update_payment_schedule()
		self.update_payment_requests()
		self.make_advance_payment_ledger_entries()
		self.update_advance_paid()  # advance_paid_status depends on the payment request amount
		self.set_status()
		payment_entry_verified(self)

class VONTOCRequestforQuotation(RequestforQuotation):
	def on_submit(self):
		self.db_set("status", "Submitted")
		for supplier in self.suppliers:
			supplier.email_sent = 0
			supplier.quote_status = "Pending"
		self.send_to_supplier()
		check_supplier(self)

class VONTOCSalesOrder(SalesOrder):
	def on_submit(self):
		self.check_credit_limit()
		self.update_reserved_qty()

		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total, self
		)
		self.update_project()
		self.update_prevdoc_status("submit")

		self.update_blanket_order()

		update_linked_doc(self.doctype, self.name, self.inter_company_order_reference)
		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

			update_coupon_code_count(self.coupon_code, "used")

		if self.get("reserve_stock"):
			self.create_stock_reservation_entries()

        # 判断是否有 advance 类型的 payment term
		has_advance = any(
			row.payment_term and row.payment_term.lower() == "advance"
			for row in self.payment_schedule
		)

		if not has_advance:
			return

		result = create_sales_invoice_or_payment_request(self.name)

class VONTOCSalesInvoice(SalesInvoice):
	def on_submit(self):
		self.validate_pos_paid_amount()

		if not self.auto_repeat:
			frappe.get_doc("Authorization Control").validate_approving_authority(
				self.doctype, self.company, self.base_grand_total, self
			)

		self.check_prev_docstatus()

		if self.is_return and not self.update_billed_amount_in_sales_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()

		self.update_billing_status_in_dn()
		self.clear_unallocated_mode_of_payments()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		if self.update_stock == 1:
			for table_name in ["items", "packed_items"]:
				if not self.get(table_name):
					continue

				self.make_bundle_for_sales_purchase_return(table_name)
				self.make_bundle_using_old_serial_batch_fields(table_name)

			self.update_stock_reservation_entries()
			self.update_stock_ledger()

		# this sequence because outstanding may get -ve
		self.make_gl_entries()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()

		if not self.is_return:
			self.update_billing_status_for_zero_amount_refdoc("Delivery Note")
			self.update_billing_status_for_zero_amount_refdoc("Sales Order")
			self.check_credit_limit()

		if not cint(self.is_pos) == 1 and not self.is_return:
			self.update_against_document_in_jv()

		self.update_time_sheet(self.name)

		if frappe.db.get_single_value("Selling Settings", "sales_update_frequency") == "Each Transaction":
			update_company_current_month_sales(self.company)
			self.update_project()
		update_linked_doc(self.doctype, self.name, self.inter_company_invoice_reference)

		# create the loyalty point ledger entry if the customer is enrolled in any loyalty program
		if not self.is_return and not self.is_consolidated and self.loyalty_program:
			self.make_loyalty_point_entry()
		elif self.is_return and self.return_against and not self.is_consolidated and self.loyalty_program:
			against_si_doc = frappe.get_doc("Sales Invoice", self.return_against)
			against_si_doc.delete_loyalty_point_entry()
			against_si_doc.make_loyalty_point_entry()
		if self.redeem_loyalty_points and not self.is_consolidated and self.loyalty_points:
			self.apply_loyalty_points()

		self.process_common_party_accounting()
		sales_invoice_submitted(self.name)

class VONTOCDeliveryNote(DeliveryNote):
	def on_submit(self):
		self.validate_packed_qty()
		self.update_pick_list_status()

		# Check for Approving Authority
		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total, self
		)

		# update delivered qty in sales order
		self.update_prevdoc_status()
		self.update_billing_status()

		self.update_stock_reservation_entries()

		if not self.is_return:
			self.check_credit_limit()
		elif self.issue_credit_note:
			self.make_return_invoice()

		for table_name in ["items", "packed_items"]:
			if not self.get(table_name):
				continue

			self.make_bundle_for_sales_purchase_return(table_name)
			self.make_bundle_using_old_serial_batch_fields(table_name)

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		self.update_stock_ledger()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()
		delivery_note_submitted(self)
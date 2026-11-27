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
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

from vontoc.vontoc.doctype.guideline_price.guideline_price import GuidelinePrice, submit_guideline_price
from frappe.utils import flt, get_link_to_form
from frappe.desk.doctype.notification_log.notification_log import (enqueue_create_notification)
from erpnext.buying.utils import validate_for_items
from erpnext.manufacturing.doctype.blanket_order.blanket_order import (validate_against_blanket_order)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (validate_inter_company_party, update_linked_doc)

from vontoc.custom_controller.status_updater import _update_prevdoc_status
from vontoc.api.purchase_receipt import stock_purchase_receipt, mirror_internal_pr
from vontoc.api.subcontracting_receipt import stock_subcontracting_receipt
from vontoc.api.subcontracting_order import subcontracting_order_submitted
from vontoc.api.purchase_order import approve_po
from vontoc.api.material_request import material_request_submitted
from vontoc.api.sales_order import sales_order_submitted

from vontoc.api.item import validate_sales_temporary_item, build_item_description
from vontoc.api.shipment import check_delivery_notes_submitted
from vontoc.api.sales_invoice import sync_sales_invoice_to_delivery_note, check_allocated_amount, Initialize_unalocated_amount
from vontoc.api.delivery_note import check_allow_shipment

from frappe.email.receive import InboundMail
from frappe.email.doctype.email_account.email_account import EmailAccount

class VONTOCPurchaseOrder(PurchaseOrder):
	def on_submit(self):
		super().on_submit()
		approve_po(self)

	def set_total_in_words(self):
		from vontoc.api.utils import money_in_words

		if self.meta.get_field("base_in_words"):
			if self.meta.get_field("base_rounded_total") and not self.is_rounded_total_disabled():
				amount = abs(flt(self.base_rounded_total))
			else:
				amount = abs(flt(self.base_grand_total))
			self.base_in_words = money_in_words(amount, self.company_currency)

		if self.meta.get_field("in_words"):
			if self.meta.get_field("rounded_total") and not self.is_rounded_total_disabled():
				amount = abs(flt(self.rounded_total))
			else:
				amount = abs(flt(self.grand_total))

			self.in_words = money_in_words(amount, self.currency)

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
		super().validate()
		#自定义逻辑
		validate_sales_temporary_item(self)
		build_item_description(self)

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

class VONTOCPurchaseInvoice(PurchaseInvoice):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.status_updater.extend(
			[
				{
					"source_dt": "Purchase Invoice Item",
					"target_dt": "Subcontracting Order Item",
					"join_field": "custom_subcontracting_order_detail",
					"target_field": "custom_billed_amt",
					"target_parent_dt": "Subcontracting Order",
					"target_parent_field": "custom_amount_billed",
					"target_ref_field": "amount",
					"source_field": "amount",
					"percent_join_field": "custom_subcontracting_order",
					"overflow_type": "billing",
				},
			]
		)

class VONTOCSalesInvoice(SalesInvoice):
	def on_update_after_submit(self):
		check_allocated_amount(self)
		sync_sales_invoice_to_delivery_note(self)

	def update_prevdoc_status(self):
		_update_prevdoc_status(self)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.status_updater.extend(
			[
				{
					"source_dt": "Sales Invoice Item",
					"target_field": "custom_billed_amt",
					"target_ref_field": "amount",
					"target_dt": "Subcontracting Receipt Supplied Item",
					"join_field": "custom_subcontracting_receipt_detail",
					"target_parent_dt": "Subcontracting Receipt",
					"target_parent_field": "custom_amount_billed",
					"source_field": "amount",
					"percent_join_field": "custom_subcontracting_receipt",
					"keyword": "Billed",
					"overflow_type": "billing",
				},
			]
		)

class VONTOCDeliveryNote(DeliveryNote):
	def on_submit(self):
		super().on_submit()
		check_allow_shipment(self)

class VONTOCSalesOrder(SalesOrder):
	def on_submit(self):
		super().on_submit()
		sales_order_submitted(self)

class CustomInboundMail(InboundMail):

	def __init__(
		self,
		content,
		email_account,
		uid=None,
		seen_status=None,
		append_to=None,
		folder_name=None,
	):
		super().__init__(
			content,
			email_account,
			uid,
			seen_status,
			append_to,
		)

		self.folder_name = folder_name

	def process(self):
		"""Create communication record from email."""
		if self.is_sender_same_as_receiver() and not self.is_reply() and self.folder_name != "Sent Items":
			if frappe.in_test:
				print("WARN: Cannot pull email. Sender same as recipient inbox")
			raise SentEmailInInboxError

		communication = self.is_exist_in_system()
		if communication:
			communication.update_db(uid=self.uid)
			data = self.as_dict()
			if data.get("bcc") and not communication.bcc:
				communication.update_db(bcc=data.get("bcc"))
			communication.reload()
			return communication

		self.flags.is_new_communication = True
		return self._build_communication_doc()

	def is_exist_in_system(self):
		"""Check if this email already exists in the system(as communication document)."""
		from frappe.core.doctype.communication.communication import Communication

		if not self.message_id:
			return

		return Communication.find_one_by_filters(
			message_id=self.message_id, order_by="creation DESC"
		)

	def as_dict(self):
		""" """
		return {
			"subject": self.subject,
			"content": self.get_content(),
			"text_content": self.text_content,
			"sent_or_received": "Sent" if self.folder_name == "Sent Items" else "Received",
			"sender_full_name": self.from_real_name,
			"sender": self.from_email,
			"recipients": self.decode_email(self.mail.get("To") or ""),
			"cc": self.decode_email(self.mail.get("CC") or ""),
			"bcc": self.decode_email(self.mail.get("BCC") or ""),
			"email_account": self.email_account.name,
			"communication_medium": "Email",
			"uid": self.uid,
			"message_id": self.message_id,
			"communication_date": self.date,
			"has_attachment": 1 if self.attachments else 0,
			"seen": self.seen_status or 0,
		}

class SentEmailInInboxError(Exception):
	pass

class CustomEmailAccount(EmailAccount):
	def get_inbound_mails(self) -> list[InboundMail]:
		"""retrive and return inbound mails."""
		mails = []

		def process_mail(messages, append_to=None, folder_name=None):
			for index, message in enumerate(messages.get("latest_messages", [])):
				uid = messages["uid_list"][index] if messages.get("uid_list") else None
				seen_status = messages.get("seen_status", {}).get(uid)
				if self.email_sync_option != "UNSEEN" or seen_status != "SEEN":
					# only append the emails with status != 'SEEN' if sync option is set to 'UNSEEN'
					mails.append(
						CustomInboundMail(
							message,
							self,
							frappe.safe_decode(uid),
							seen_status,
							append_to,
							folder_name,
						)
					)

		if not self.enable_incoming:
			return []

		try:
			if self.service == "Frappe Mail":
				frappe_mail_client = self.get_frappe_mail_client()
				messages = frappe_mail_client.pull_raw(last_received_at=self.last_received_at)
				process_mail(messages)
				self.db_set("last_received_at", messages["last_received_at"], update_modified=False)
			else:
				email_sync_rule = self.build_email_sync_rule()
				email_server = self.get_incoming_server(in_receive=True, email_sync_rule=email_sync_rule)
				if self.use_imap:
					# process all given imap folder
					for folder in self.imap_folder:
						if email_server.select_imap_folder(folder.folder_name):
							email_server.settings["uid_validity"] = folder.uidvalidity
							messages = email_server.get_messages(folder=f'"{folder.folder_name}"') or {}
							process_mail(messages, folder.append_to, folder.folder_name,)
				else:
					# process the pop3 account
					messages = email_server.get_messages() or {}
					process_mail(messages)

				# close connection to mailserver
				email_server.logout()
		except Exception:
			self.log_error(title=_("Error while connecting to email account {0}").format(self.name))
			return []

		return mails

import json
import frappe
from frappe import _
from frappe.desk.form.document_follow import follow_document
from frappe.utils.data import strip_html
from erpnext.accounts.party import get_party_account_currency
from frappe.utils import cstr, flt, strip_html
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.contacts.doctype.address.address import get_company_address
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults

@frappe.whitelist()
def add(args=None, *, ignore_permissions=False):
	"""add in someone's to do list
	args = {
	        "assign_to": [],
	        "doctype": ,
	        "name": ,
	        "description": ,
	        "assignment_rule":
	}

	"""
	if not args:
		args = frappe.local.form_dict

	users_with_duplicate_todo = []
	shared_with_users = []

	for assign_to in frappe.parse_json(args.get("assign_to")):
		filters = {
			"reference_type": args["doctype"],
			"reference_name": args["name"],
			"status": "Open",
			"allocated_to": assign_to,
		}
		if not ignore_permissions:
			frappe.get_doc(args["doctype"], args["name"]).check_permission()

		if frappe.get_all("ToDo", filters=filters):
			users_with_duplicate_todo.append(assign_to)
		else:
			from frappe.utils import nowdate

			description = args.get("description") or ""
			has_content = strip_html(description) or "<img" in description
			if not has_content:
				args["description"] = _("Assignment for {0} {1}").format(args["doctype"], args["name"])

			d = frappe.get_doc(
				{
					"doctype": "ToDo",
					"allocated_to": assign_to,
					"reference_type": args["doctype"],
					"reference_name": str(args["name"]),
					"description": args.get("description"),
					"priority": args.get("priority", "Medium"),
					"status": "Open",
					"date": args.get("date", nowdate()),
					"assigned_by": args.get("assigned_by", frappe.session.user),
					"assignment_rule": args.get("assignment_rule"),
				}
			).insert(ignore_permissions=True)

			# set assigned_to if field exists
			if frappe.get_meta(args["doctype"]).get_field("assigned_to"):
				frappe.db.set_value(args["doctype"], args["name"], "assigned_to", assign_to)

			doc = frappe.get_doc(args["doctype"], args["name"])

			# if assignee does not have permissions, share or inform
			if not frappe.has_permission(doc=doc, user=assign_to):
				if frappe.get_system_settings("disable_document_sharing"):
					msg = _("User {0} is not permitted to access this document.").format(
						frappe.bold(assign_to)
					)
					msg += "<br>" + _(
						"As document sharing is disabled, please give them the required permissions before assigning."
					)
					frappe.throw(msg, title=_("Missing Permission"))
				else:
					frappe.share.add(doc.doctype, doc.name, assign_to)
					shared_with_users.append(assign_to)

			# make this document followed by assigned user
			if frappe.get_cached_value("User", assign_to, "follow_assigned_documents"):
				follow_document(args["doctype"], args["name"], assign_to)

			# 取消notification

	if shared_with_users:
		user_list = format_message_for_assign_to(shared_with_users)
		frappe.msgprint(
			_("Shared with the following Users with Read access:{0}").format(user_list, alert=True)
		)

	if users_with_duplicate_todo:
		user_list = format_message_for_assign_to(users_with_duplicate_todo)
		frappe.msgprint(_("Already in the following Users ToDo list:{0}").format(user_list, alert=True))

	return get(args)

def format_message_for_assign_to(users):
	return "<br><br>" + "<br>".join(users)

def get(args=None):
	"""get assigned to"""
	if not args:
		args = frappe.local.form_dict

	return frappe.get_all(
		"ToDo",
		fields=["allocated_to as owner", "name"],
		filters={
			"reference_type": args.get("doctype"),
			"reference_name": args.get("name"),
			"status": ("not in", ("Cancelled", "Closed")),
		},
		limit=5,
	)

@frappe.whitelist()
def create_supplier_quotation(doc):
	if isinstance(doc, str):
		doc = json.loads(doc)

	try:
		sq_doc = frappe.get_doc(
			{
				"doctype": "Supplier Quotation",
				"supplier": doc.get("supplier"),
				"terms": doc.get("terms"),
				"custom_notes": doc.get("custom_notes"),
				"company": doc.get("company"),
				"currency": doc.get("currency")
				or get_party_account_currency("Supplier", doc.get("supplier"), doc.get("company")),
				"buying_price_list": doc.get("buying_price_list")
				or frappe.db.get_value("Buying Settings", None, "buying_price_list"),
			}
		)
		add_items(sq_doc, doc.get("supplier"), doc.get("items"))
		sq_doc.flags.ignore_permissions = True
		sq_doc.run_method("set_missing_values")
		sq_doc.save()
		frappe.msgprint(_("Supplier Quotation {0} Created").format(sq_doc.name))
		return sq_doc.name
	except Exception:
		return None
	
def add_items(sq_doc, supplier, items):
	for data in items:
		if isinstance(data, dict):
			data = frappe._dict(data)

		create_rfq_items(sq_doc, supplier, data)

def create_rfq_items(sq_doc, supplier, data):
	args = {}

	for field in [
		"item_code",
		"item_name",
		"description",
		"qty",
		"rate",
		"conversion_factor",
		"warehouse",
		"material_request",
		"material_request_item",
		"stock_qty",
		"uom",
	]:
		args[field] = data.get(field)

	args.update(
		{
			"request_for_quotation_item": data.name,
			"request_for_quotation": data.parent,
			"supplier_part_no": frappe.db.get_value(
				"Item Supplier", {"parent": data.item_code, "supplier": supplier}, "supplier_part_no"
			),
		}
	)

	sq_doc.append("items", args)

@frappe.whitelist()
def make_inter_company_sales_order(source_name, target_doc=None):

	return make_inter_company_transaction("Purchase Order", source_name, target_doc)

def make_inter_company_transaction(doctype, source_name, target_doc=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
		get_received_items, 
		get_inter_company_details,
		set_purchase_references,
		update_address,
		update_taxes,
		)
	from frappe.model.mapper import get_mapped_doc
	from frappe.utils import flt

	if doctype in ["Sales Invoice", "Sales Order"]:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Purchase Invoice" if doctype == "Sales Invoice" else "Purchase Order"
		target_detail_field = "sales_invoice_item" if doctype == "Sales Invoice" else "sales_order_item"
		source_document_warehouse_field = "target_warehouse"
		target_document_warehouse_field = "from_warehouse"
		received_items = get_received_items(source_name, target_doctype, target_detail_field)
	else:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Sales Invoice" if doctype == "Purchase Invoice" else "Sales Order"
		source_document_warehouse_field = "from_warehouse"
		target_document_warehouse_field = "target_warehouse"
		received_items = {}

	validate_inter_company_transaction(source_doc, doctype)
	details = get_inter_company_details(source_doc, doctype)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		set_purchase_references(target)

	def update_details(source_doc, target_doc, source_parent):
		def _validate_address_link(address, link_doctype, link_name):
			return frappe.db.get_value(
				"Dynamic Link",
				{
					"parent": address,
					"parenttype": "Address",
					"link_doctype": link_doctype,
					"link_name": link_name,
				},
				"parent",
			)

		target_doc.inter_company_invoice_reference = source_doc.name
		if target_doc.doctype in ["Purchase Invoice", "Purchase Order"]:
			currency = frappe.db.get_value("Supplier", details.get("party"), "default_currency")
			target_doc.company = details.get("company")
			target_doc.supplier = details.get("party")
			target_doc.is_internal_supplier = 1
			target_doc.ignore_pricing_rule = 1
			target_doc.buying_price_list = source_doc.selling_price_list

			# Invert Addresses
			if source_doc.company_address and _validate_address_link(
				source_doc.company_address, "Supplier", details.get("party")
			):
				update_address(target_doc, "supplier_address", "address_display", source_doc.company_address)
			if source_doc.dispatch_address_name and _validate_address_link(
				source_doc.dispatch_address_name, "Company", details.get("company")
			):
				update_address(
					target_doc,
					"dispatch_address",
					"dispatch_address_display",
					source_doc.dispatch_address_name,
				)
			if source_doc.shipping_address_name and _validate_address_link(
				source_doc.shipping_address_name, "Company", details.get("company")
			):
				update_address(
					target_doc,
					"shipping_address",
					"shipping_address_display",
					source_doc.shipping_address_name,
				)
			if source_doc.customer_address and _validate_address_link(
				source_doc.customer_address, "Company", details.get("company")
			):
				update_address(
					target_doc, "billing_address", "billing_address_display", source_doc.customer_address
				)

			if currency:
				target_doc.currency = currency

			update_taxes(
				target_doc,
				party=target_doc.supplier,
				party_type="Supplier",
				company=target_doc.company,
				doctype=target_doc.doctype,
				party_address=target_doc.supplier_address,
				company_address=target_doc.shipping_address,
			)

		else:
			currency = frappe.db.get_value("Customer", details.get("party"), "default_currency")
			target_doc.company = details.get("company")
			target_doc.customer = details.get("party")
			target_doc.selling_price_list = source_doc.buying_price_list

			if source_doc.supplier_address and _validate_address_link(
				source_doc.supplier_address, "Company", details.get("company")
			):
				update_address(
					target_doc, "company_address", "company_address_display", source_doc.supplier_address
				)
			if source_doc.shipping_address and _validate_address_link(
				source_doc.shipping_address, "Customer", details.get("party")
			):
				update_address(
					target_doc, "shipping_address_name", "shipping_address", source_doc.shipping_address
				)
			if source_doc.shipping_address and _validate_address_link(
				source_doc.shipping_address, "Customer", details.get("party")
			):
				update_address(target_doc, "customer_address", "address_display", source_doc.shipping_address)

			if currency:
				target_doc.currency = currency

			update_taxes(
				target_doc,
				party=target_doc.customer,
				party_type="Customer",
				company=target_doc.company,
				doctype=target_doc.doctype,
				party_address=target_doc.customer_address,
				company_address=target_doc.company_address,
				shipping_address_name=target_doc.shipping_address_name,
			)

	def update_item(source, target, source_parent):
		target.qty = flt(source.qty) - received_items.get(source.name, 0.0)
		if source.doctype == "Purchase Order Item" and target.doctype == "Sales Order Item":
			target.purchase_order = source.parent
			target.purchase_order_item = source.name
			target.material_request = source.material_request
			target.material_request_item = source.material_request_item

		if (
			source.get("purchase_order")
			and source.get("purchase_order_item")
			and target.doctype == "Purchase Invoice Item"
		):
			target.purchase_order = source.purchase_order
			target.po_detail = source.purchase_order_item

		if (source.get("serial_no") or source.get("batch_no")) and not source.get("serial_and_batch_bundle"):
			target.use_serial_batch_fields = 1

	item_field_map = {
		"doctype": target_doctype + " Item",
		"field_no_map": ["income_account", "expense_account", "cost_center", "warehouse"],
		"field_map": {
			"rate": "rate",
		},
		"postprocess": update_item,
		"condition": lambda doc: doc.qty > 0,
	}

	if doctype in ["Sales Invoice", "Sales Order"]:
		item_field_map["field_map"].update(
			{
				"name": target_detail_field,
			}
		)

	if source_doc.get("update_stock"):
		item_field_map["field_map"].update(
			{
				source_document_warehouse_field: target_document_warehouse_field,
				"batch_no": "batch_no",
				"serial_no": "serial_no",
			}
		)
	elif target_doctype == "Sales Order":
		item_field_map["field_map"].update(
			{
				source_document_warehouse_field: "warehouse",
			}
		)

	doclist = get_mapped_doc(
		doctype,
		source_name,
		{
			doctype: {
				"doctype": target_doctype,
				"postprocess": update_details,
				"set_target_warehouse": "set_from_warehouse",
				"field_no_map": ["taxes_and_charges", "set_warehouse", "shipping_address", "conversion_rate", "plc_conversion_rate"],
			},
			doctype + " Item": item_field_map,
		},
		target_doc,
		set_missing_values,
	)

	return doclist

def validate_inter_company_transaction(doc, doctype):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
		get_inter_company_details
		)
	
	details = get_inter_company_details(doc, doctype)
	price_list = (
		doc.selling_price_list
		if doctype in ["Sales Invoice", "Sales Order", "Delivery Note"]
		else doc.buying_price_list
	)
	valid_price_list = frappe.db.get_value("Price List", {"name": price_list, "buying": 1, "selling": 1})
	if not valid_price_list and not doc.is_internal_transfer():
		frappe.throw(_("Selected Price List should have buying and selling fields checked."))

	party = details.get("party")
	if not party:
		partytype = "Supplier" if doctype in ["Sales Invoice", "Sales Order"] else "Customer"
		frappe.throw(_("No {0} found for Inter Company Transactions.").format(partytype))

	"""company = details.get("company")
	default_currency = frappe.get_cached_value("Company", company, "default_currency")
	if default_currency != doc.currency:
		frappe.throw(
			_("Company currencies of both the companies should match for Inter Company Transactions.")
		)
	"""
	return

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, kwargs=None):
	from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
	from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
		get_sre_details_for_voucher,
		get_sre_reserved_qty_details_for_voucher,
		get_ssb_bundle_for_voucher,
	)

	if not kwargs:
		kwargs = {
			"for_reserved_stock": frappe.flags.args and frappe.flags.args.for_reserved_stock,
			"skip_item_mapping": frappe.flags.args and frappe.flags.args.skip_item_mapping,
		}

	kwargs = frappe._dict(kwargs)

	sre_details = {}
	if kwargs.for_reserved_stock:
		sre_details = get_sre_reserved_qty_details_for_voucher("Sales Order", source_name)

	mapper = {
		"Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
		"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
		"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
	}

	# 0 qty is accepted, as the qty is uncertain for some items
	has_unit_price_items = frappe.db.get_value("Sales Order", source_name, "has_unit_price_items")

	def is_unit_price_row(source):
		return has_unit_price_items and source.qty == 0

	def select_item(d):
		filtered_items = kwargs.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	def set_missing_values(source, target):
		if kwargs.get("ignore_pricing_rule"):
			# Skip pricing rule when the dn is creating from the pick list
			target.ignore_pricing_rule = 1

		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_use_serial_batch_fields")

		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Delivery Note", "company_address", target.company_address))

		# if invoked in bulk creation, validations are ignored and thus this method is nerver invoked
		if frappe.flags.bulk_transaction:
			# set target items names to ensure proper linking with packed_items
			target.set_new_name()

		make_packing_list(target)

	def condition(doc):
		if doc.name in sre_details:
			del sre_details[doc.name]
			return False

		# make_mapped_doc sets js `args` into `frappe.flags.args`
		if frappe.flags.args and frappe.flags.args.delivery_dates:
			if cstr(doc.delivery_date) not in frappe.flags.args.delivery_dates:
				return False
		if frappe.flags.args and frappe.flags.args.until_delivery_date:
			if cstr(doc.delivery_date) > frappe.flags.args.until_delivery_date:
				return False

		return (
			(abs(doc.delivered_qty) < abs(doc.qty)) or is_unit_price_row(doc)
		) and doc.delivered_by_supplier != 1

	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = (
			flt(source.qty) if is_unit_price_row(source) else flt(source.qty) - flt(source.delivered_qty)
		)

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)

		if item:
			target.cost_center = (
				frappe.db.get_value("Project", source_parent.project, "cost_center")
				or item.get("buying_cost_center")
				or item_group.get("buying_cost_center")
			)

	if not kwargs.skip_item_mapping:
		mapper["Sales Order Item"] = {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"condition": lambda d: condition(d) and select_item(d) and select_stock_item(d)
		}
		
	def select_stock_item(d):
		return frappe.db.get_value(
			"Item",
			d.item_code,
			"is_stock_item"
		)

	so = frappe.get_doc("Sales Order", source_name)
	target_doc = get_mapped_doc("Sales Order", so.name, mapper, target_doc)

	if not kwargs.skip_item_mapping and kwargs.for_reserved_stock:
		sre_list = get_sre_details_for_voucher("Sales Order", source_name)

		if sre_list:

			def update_dn_item(source, target, source_parent):
				update_item(source, target, so)

			so_items = {d.name: d for d in so.items if d.stock_reserved_qty}

			for sre in sre_list:
				if not condition(so_items[sre.voucher_detail_no]):
					continue

				dn_item = get_mapped_doc(
					"Sales Order Item",
					sre.voucher_detail_no,
					{
						"Sales Order Item": {
							"doctype": "Delivery Note Item",
							"field_map": {
								"rate": "rate",
								"name": "so_detail",
								"parent": "against_sales_order",
							},
							"postprocess": update_dn_item,
						}
					},
					ignore_permissions=True,
				)

				dn_item.qty = flt(sre.reserved_qty) / flt(dn_item.get("conversion_factor", 1))
				dn_item.warehouse = sre.warehouse

				use_serial_batch_fields = frappe.get_single_value("Stock Settings", "use_serial_batch_fields")

				if (
					not use_serial_batch_fields
					and sre.reservation_based_on == "Serial and Batch"
					and (sre.has_serial_no or sre.has_batch_no)
				):
					dn_item.serial_and_batch_bundle = get_ssb_bundle_for_voucher(sre)

				target_doc.append("items", dn_item)
			else:
				# Correct rows index.
				for idx, item in enumerate(target_doc.items):
					item.idx = idx + 1

	if not kwargs.skip_item_mapping and frappe.flags.bulk_transaction and not target_doc.items:
		# the (date) condition filter resulted in an unintendedly created empty DN; remove it
		del target_doc
		return

	# Should be called after mapping items.
	set_missing_values(so, target_doc)

	return target_doc

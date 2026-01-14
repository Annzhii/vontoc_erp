import json
import frappe
from frappe import _
from frappe.desk.form.document_follow import follow_document
from frappe.utils.data import strip_html
from erpnext.accounts.party import get_party_account_currency


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
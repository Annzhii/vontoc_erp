import frappe
import json
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference 
from vontoc.utils.process_engine import process_flow_engine
from erpnext.accounts.party import get_party_account
from frappe.utils import flt
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def subcontracting_order_submitted (doc):

    pf_name = get_process_flow_trace_id_by_reference("Subcontracting Order", [doc.name])
    to_close = [
        {
            "doctype": "Subcontracting Order",
            "docname": doc.name
        }
    ]

    to_open = [{
        "doctype": "Subcontracting Order",
        "docname": doc.name,
        "user": "Purchase Manager",
        "description": "跟进供应商发货进度，核对到货数量和质量，并提交采分包货单（Subcontracting Receipt）。",
    }]

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None, args=None):
	return get_mapped_purchase_invoice(source_name, target_doc, args=args)

def get_mapped_purchase_invoice(source_name, target_doc=None, ignore_permissions=False, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	def postprocess(source, target):
		target.flags.ignore_permissions = ignore_permissions
		set_missing_values(source, target)

		# Get the advance paid Journal Entries in Purchase Invoice Advance
		if target.get("allocate_advances_automatically"):
			target.set_advances()

		target.set_payment_schedule()
		target.credit_to = get_party_account("Supplier", source.supplier, source.company)

	def update_item(obj, target, source_parent):
		def get_billed_qty(po_item_name):
			from frappe.query_builder.functions import Sum

			table = frappe.qb.DocType("Purchase Invoice Item")
			query = (
				frappe.qb.from_(table)
				.select(Sum(table.qty).as_("qty"))
				.where((table.docstatus == 1) & (table.custom_subcontracting_order_detail == po_item_name))
			)
			return query.run(pluck="qty")[0] or 0

		billed_qty = flt(get_billed_qty(obj.name))
		target.qty = flt(obj.qty) - billed_qty

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)
		target.cost_center = (
			obj.cost_center
			or frappe.db.get_value("Project", obj.project, "cost_center")
			or item.get("buying_cost_center")
			or item_group.get("buying_cost_center")
		)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	fields = {
		"Subcontracting Order": {
			"doctype": "Purchase Invoice",
			"field_map": {
				"party_account_currency": "party_account_currency",
				"supplier_warehouse": "supplier_warehouse",
			},
			"field_no_map": ["payment_terms_template"],
			"validation": {
				"docstatus": ["=", 1],
			},
		},
		"Subcontracting Order Item": {
			"doctype": "Purchase Invoice Item",
			"field_map": {
				"name": "custom_subcontracting_order_detail",
				"parent": "custom_subcontracting_order",
				"material_request": "material_request",
				"material_request_item": "material_request_item",
				"wip_composite_asset": "wip_composite_asset",
			},
			"postprocess": update_item,
			"condition": lambda doc: (doc.amount == 0 or abs(doc.custom_billed_amt) < abs(doc.amount))
			and select_item(doc),
		},
		"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges", "reset_value": True},
	}

	doc = get_mapped_doc(
		"Subcontracting Order",
		source_name,
		fields,
		target_doc,
		postprocess,
		ignore_permissions=ignore_permissions,
	)

	return doc

def set_missing_values(source, target):
	target.selling_price_list = "Standard Buying"
	target.currency = frappe.db.get_value(
		"Price List",
		target.buying_price_list,
		"currency"
	)
	target.run_method("set_missing_values")
	target.run_method("calculate_taxes_and_totals")
	target.run_method("set_use_serial_batch_fields")
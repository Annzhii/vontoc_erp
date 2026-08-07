import json
import frappe
from frappe import _
from frappe.utils import flt, cint
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.utils import is_source_fully_generated, get_suppliers_warehouse_name, if_full_received
from frappe.workflow.doctype.workflow_action.workflow_action import apply_workflow
from erpnext.controllers.accounts_controller import merge_taxes
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Abs, Sum
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.utils import get_fetch_values
from erpnext.accounts.party import get_party_account
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults

@frappe.whitelist()
def send_subcontracting_receipt(docname):
    sub_pr = frappe.get_doc("Subcontracting Receipt", docname)
    sub_pos = set()
    for item in sub_pr.items:
        sub_pos.add(item.subcontracting_order)

    to_close = [
        {
            "doctype": "Subcontracting Order",
            "docname": sub_po,
        }
        for sub_po in sub_pos if is_source_fully_generated(
            {
                "source_doc": {"doctype": "Subcontracting Order", "docname": sub_po},
                "generated_doc": {"doctype": "Subcontracting Receipt", "field": "subcontracting_order"}
            })
    ]

    suppliers_group_warehouse = get_suppliers_warehouse_name(sub_pr.company)
    supplier_warehouse = frappe.get_doc("Warehouse", sub_pr.set_warehouse)
    
    if supplier_warehouse.parent_warehouse == suppliers_group_warehouse:
        user = "Robot"
        auto_stock = True
    else:
        user = "Stock Manager"
        auto_stock = False

    to_open = [{
        "doctype": "Subcontracting Receipt",
        "docname": sub_pr.name,
        "user": user,
        "description": "收到货物后，核对到货数量与收货单（Subcontracting Receipt）中记录的数量是否一致。确认无误后，完成入库操作，并更新库存记录。",
    }]

    pf_name = get_process_flow_trace_id_by_reference("Subcontracting Order", sub_pos)

    process_flow_trace_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Subcontracting Receipt",
        "ref_docname": sub_pr.name,
        "todo_name": None
    }

    if not pf_name:
        return
    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info=process_flow_trace_info)
    if auto_stock:
        apply_workflow(sub_pr, "Stock")

def stock_subcontracting_receipt(docname):
    
    sub_pr = frappe.get_doc("Subcontracting Receipt", docname)

    to_close = [{
        "doctype": "Subcontracting Receipt",
        "docname": docname
    }]

    sub_pos = set()
    for item in sub_pr.items:
        sub_pos.add(item.subcontracting_order)

    pos = set()
    for sub_po in sub_pos:
        sub_po = frappe.get_doc("Subcontracting Order", sub_po)
        po = sub_po.purchase_order
        pos.add(po)
    
    mrs = set()
    for po in pos:
        po = frappe.get_doc("Purchase Order", po)
        for item in po.items:
            mrs.add(item.material_request)
    for mr in mrs:
        full_received = if_full_received(mr)
        if full_received == False:
            trace = ""
        else:
            trace = "close"

        pf_name = get_process_flow_trace_id_by_reference("Material Request", [mr])

        process_flow_trace_info = {
            "trace": trace,
            "pf_name": pf_name,
            "todo_name": None
        }
        if not pf_name:
            return
        process_flow_engine(to_close=to_close, process_flow_trace_info=process_flow_trace_info)

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	from erpnext.accounts.party import get_payment_terms_template

	doc = frappe.get_doc("Subcontracting Receipt", source_name)
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		if len(target.get("items")) == 0:
			frappe.throw(_("All items have already been Invoiced/Returned"))

		doc = frappe.get_doc(target)
		doc.payment_terms_template = get_payment_terms_template(source.supplier, "Supplier", source.company)
		doc.run_method("onload")
		doc.run_method("set_missing_values")

		if args and args.get("merge_taxes"):
			merge_taxes(source, doc)

		doc.run_method("calculate_taxes_and_totals")
		doc.set_payment_schedule()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty, returned_qty = get_pending_qty(source_doc)
		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			target_doc.rejected_qty = 0
		target_doc.stock_qty = flt(target_doc.qty) * flt(
			target_doc.conversion_factor, target_doc.precision("conversion_factor")
		)
		returned_qty_map[source_doc.name] = returned_qty
		target_doc._old_name = source_doc.name

	def get_pending_qty(item_row):
		qty = item_row.qty
		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			qty = item_row.received_qty

		pending_qty = qty - invoiced_qty_map.get(item_row.name, 0)

		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			return pending_qty, 0

		returned_qty = flt(returned_qty_map.get(item_row.name, 0))
		if item_row.rejected_qty and returned_qty:
			returned_qty -= item_row.rejected_qty

		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0

		return pending_qty, returned_qty

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	doclist = get_mapped_doc(
		"Subcontracting Receipt",
		source_name,
		{
			"Subcontracting Receipt": {
				"doctype": "Purchase Invoice",
				"field_map": {
					"supplier_warehouse": "supplier_warehouse",
					"is_return": "is_return",
					"bill_date": "bill_date",
				},
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Subcontracting Receipt Item": {
				"doctype": "Purchase Invoice Item",
				"field_map": {
					"name": "custom_subcontracting_receipt_detail",
					"parent": "custom_subcontracting_receipt",
					"qty": "received_qty",
					"is_fixed_asset": "is_fixed_asset",
					"asset_location": "asset_location",
					"asset_category": "asset_category",
					"wip_composite_asset": "wip_composite_asset",
				},
				"postprocess": update_item,
				"filter": lambda d: (
					get_pending_qty(d)[0] <= 0 if not doc.get("is_return") else get_pending_qty(d)[0] > 0
				),
				"condition": select_item,
			},
			"Purchase Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
				"reset_value": not (args and args.get("merge_taxes")),
				"ignore": args.get("merge_taxes") if args else 0,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist

def get_invoiced_qty_map(purchase_receipt):
	"""returns a map: {custom_subcontracting_receipt_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for custom_subcontracting_receipt_detail, qty in frappe.db.sql(
		"""select custom_subcontracting_receipt_detail, qty from `tabPurchase Invoice Item`
		where custom_subcontracting_receipt=%s and docstatus=1""",
		purchase_receipt,
	):
		if not invoiced_qty_map.get(custom_subcontracting_receipt_detail):
			invoiced_qty_map[custom_subcontracting_receipt_detail] = 0
		invoiced_qty_map[custom_subcontracting_receipt_detail] += qty

	return invoiced_qty_map


def get_returned_qty_map(purchase_receipt):
	"""returns a map: {custom_subcontracting_receipt_detail: returned_qty}"""

	pr = frappe.qb.DocType("Subcontracting Receipt")
	pr_item = frappe.qb.DocType("Subcontracting Receipt Item")

	query = (
		frappe.qb.from_(pr)
		.inner_join(pr_item)
		.on(pr.name == pr_item.parent)
		.select(pr_item.subcontracting_receipt_item, Sum(Abs(pr_item.qty)).as_("qty"))
		.where(
			(pr.docstatus == 1)
			& (pr.is_return == 1)
			& (pr.return_against == purchase_receipt)
			& (pr_item.subcontracting_receipt_item.isnotnull())
		)
		.groupby(pr_item.subcontracting_receipt_item)
	).run(as_list=1)

	return frappe._dict(query) if query else frappe._dict()

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False, args=None):
	from vontoc.api.supplier import create_customer_from_supplier

	source = frappe.get_doc("Subcontracting Receipt", source_name)

	if not frappe.db.exists("Customer", source.supplier):
		create_customer_from_supplier(
			source.supplier,
			source.company
		)
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	def postprocess(source, target):
		set_missing_values(source, target)
		# Get the advance paid Journal Entries in Sales Invoice Advance
		if target.get("allocate_advances_automatically"):
			target.set_advances()

	def set_missing_values(source, target):
		target.selling_price_list = "Cost Price"
		target.currency = frappe.db.get_value(
			"Price List",
			target.selling_price_list,
			"currency"
		)
		target.flags.ignore_permissions = True
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_use_serial_batch_fields")

		if source.shipping_address:
			target.update({"company_address": source.shipping_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", "company_address", target.company_address))

		target.debit_to = get_party_account("Customer", source.supplier, source.company)

	def update_item(source, target, source_parent):
		def get_billed_qty(sr_item_name):
			from frappe.query_builder.functions import Sum

			table = frappe.qb.DocType("Sales Invoice Item")
			query = (
				frappe.qb.from_(table)
				.select(Sum(table.qty).as_("qty"))
				.where((table.docstatus == 1) & (table.custom_subcontracting_receipt_detail == sr_item_name))
			)
			return query.run(pluck="qty")[0] or 0

		target.amount = flt(source.amount) - flt(source.custom_billed_amt)

		#target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = source.consumed_qty - get_billed_qty(source.name)

	doclist = get_mapped_doc(
		"Subcontracting Receipt",
		source_name,
		{
			"Subcontracting Receipt": {
				"doctype": "Sales Invoice",
				"field_map": {
					"party_account_currency": "party_account_currency",
					"supplier":"customer"
				},
				"field_no_map": ["payment_terms_template", "currency", "conversion_rate"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Subcontracting Receipt Supplied Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"name": "custom_subcontracting_receipt_detail",
					"parent": "custom_subcontracting_receipt",
					"consumed_qty":"qty",
					"rm_item_code":"item_code",
				},
				"postprocess": update_item,
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"reset_value": True,
			},
			"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
		},
		target_doc,
		postprocess,
		ignore_permissions=ignore_permissions,
	)

	automatically_fetch_payment_terms = cint(
		frappe.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)
	if automatically_fetch_payment_terms:
		doclist.set_payment_schedule()

	return doclist
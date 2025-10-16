import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from vontoc.utils.process_engine import process_flow_engine
from frappe import _
import json
from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
)
from frappe.utils import add_days, cint, nowdate, strip_html

@frappe.whitelist()
def create_sales_invoice_or_payment_request(sales_order_name):
    doc = frappe.get_doc("Sales Order", sales_order_name)

    # 判断是否有 'Advance' 类型的 payment_term
    advance_amount = sum(
        row.payment_amount
        for row in doc.payment_schedule
        if row.payment_term and row.payment_term.lower() == "advance"
    )

    if not advance_amount:
        return {"status": "no_advance", "message": "No advance payment term found."}

    if doc.get("custom_deposit_invoice") == 1:
        process_flow_trace_info = {
            "trace": "setup",
            "pf_type": "Advance",
            "ref_doctype": "Sales Order",
            "ref_docname": doc.name,
            "todo_name": None
        }
        pf_name = process_flow_engine(process_flow_trace_info=process_flow_trace_info)

        sales_invoice = make_sales_invoice(sales_order_name)
        sales_invoice.insert(ignore_permissions=True)

        to_open = [{
            "doctype": "Sales Invoice",
            "docname": sales_invoice.name,
            "user": "Sales",
            "description": "请检查预收款发票的金额，并且发送给客户。",
        }]

        _process_flow_trace_info = {
            "trace": "add",
            "pf_name": pf_name,
            "ref_doctype": "Sales Invoice",
            "ref_docname": sales_invoice.name,
            "todo_name": None
        }
        process_flow_engine(to_open=to_open, process_flow_trace_info=_process_flow_trace_info)

    else:
        process_flow_trace_info = {
            "trace": "setup",
            "pf_type": "Advance",
            "ref_doctype": "Sales Order",
            "ref_docname": doc.name,
            "todo_name": None
        }
        pf_name = process_flow_engine(process_flow_trace_info=process_flow_trace_info)

        # 获取或创建 Payment Request
        payment_request = make_payment_request(
            dt="Sales Order",
            dn=doc.name,
            recipient_id=doc.customer,
            payment_request_type="Inward",
            #grand_total=advance_amount,
            # mode_of_payment=frappe.db.get_single_value("Accounts Settings", "default_mode_of_payment"),
            mute_email=True
        )
        #payment_request.insert(ignore_permissions=True)

        to_open = [{
            "doctype": "Payment Request",
            "docname": payment_request.name,
            "user": "approver",
            "description": "请提交付款请求。",
        }]
        _process_flow_trace_info = {
            "trace": "add",
            "pf_name": pf_name,
            "ref_doctype": "Payment Request",
            "ref_docname": payment_request.name,
            "todo_name": None
        }
        process_flow_engine(to_open=to_open, process_flow_trace_info=_process_flow_trace_info)

@frappe.whitelist()
def make_raw_material_request(items, company, sales_order, project=None):
	if not frappe.has_permission("Sales Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if isinstance(items, str):
		items = frappe._dict(json.loads(items))

	for item in items.get("items"):
		item["include_exploded_items"] = items.get("include_exploded_items")
		item["ignore_existing_ordered_qty"] = items.get("ignore_existing_ordered_qty")
		item["include_raw_materials_from_sales_order"] = items.get("include_raw_materials_from_sales_order")

	items.update({"company": company, "sales_order": sales_order})

	item_wh = {}
	for item in items.get("items"):
		if item.get("warehouse"):
			item_wh[item.get("item_code")] = item.get("warehouse")

	raw_materials = get_items_for_material_requests(items)
	if not raw_materials:
		frappe.msgprint(_("Material Request not created, as quantity for Raw Materials already available."))
		return

	material_request = frappe.new_doc("Material Request")
	material_request.update(
		dict(
			doctype="Material Request",
			transaction_date=nowdate(),
			company=company,
			material_request_type="Purchase",
		)
	)
	for item in raw_materials:
		item_doc = frappe.get_cached_doc("Item", item.get("item_code"))

		schedule_date = add_days(nowdate(), cint(item_doc.lead_time_days))
		row = material_request.append(
			"items",
			{
				"item_code": item.get("item_code"),
				"qty": item.get("quantity"),
				"schedule_date": schedule_date,
				"warehouse": item_wh.get(item.get("main_bom_item")) or item.get("warehouse"),
				"sales_order": sales_order,
				"project": project,
			},
		)

		if not (strip_html(item.get("description")) and strip_html(item_doc.description)):
			row.description = item_doc.item_name or item.get("item_code")

	material_request.insert()
	material_request.flags.ignore_permissions = 1
	material_request.run_method("set_missing_values")
	#material_request.submit()
	return material_request
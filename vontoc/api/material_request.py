import frappe
import json
from frappe import _
from vontoc.utils.process_engine import process_flow_engine
from frappe.utils import flt, getdate, nowdate
from erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom import (
	get_subcontracting_boms_for_finished_goods,
)
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import get_default_bom
from frappe.utils import add_days, cint, flt, nowdate, strip_html
from erpnext.manufacturing.doctype.production_plan.production_plan import get_items_for_material_requests

@frappe.whitelist()
def material_request_submitted (doc):
    if doc.material_request_type == "Purchase" and doc.buying_price_list == "Standard Buying":
        process_flow_trace_info={
            "trace": "setup",
            "pf_type": "Purchase",
            "ref_doctype": "Material Request",
            "ref_docname": doc.name,
        }
        #if trace is set_up，process_flow_engine returns pf_name
        pf_name = process_flow_engine(process_flow_trace_info=process_flow_trace_info)
        
        #流程第二步启动
        process_flow_trace_info={
            "pf_name": [pf_name],
            "trace": "add",
            "mark": "1",
        }
        to_open = [{
            "doctype": "Material Request",
            "docname": doc.name,
            "user": "Purchase Manager",
            "description": "审核收到的物料申请（Material Request），确认物料种类、数量和预算是否合理。如符合要求，生成采购订单；如有问题，反馈相关部门并处理。",
        }]
        process_flow_engine(to_open=to_open, process_flow_trace_info=process_flow_trace_info)

    elif doc.material_request_type == "Purchase" and doc.buying_price_list == "Internal Price":
        make_purchase_order(doc.name, is_internal=True, not_return_doclist =True)

@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None, args=None, is_internal=None, not_return_doclist=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	is_subcontracted = (
		frappe.db.get_value("Material Request", source_name, "material_request_type") == "Subcontracting"
	)

	def postprocess(source, target_doc):
		target_doc.is_subcontracted = is_subcontracted
		if is_internal:
			internal_supplier = frappe.db.get_value(
				"Supplier",
				{
					"is_internal_supplier": 1,
					"disabled": 0
				},
				"name"
			)
			if not internal_supplier:
				frappe.throw(_("Internal Supplier is not configured"))
			target_doc.supplier = internal_supplier
		if frappe.flags.args and frappe.flags.args.default_supplier:
			# items only for given default supplier
			supplier_items = []
			for d in target_doc.items:
				if is_subcontracted and not d.item_code:
					continue
				default_supplier = get_item_defaults(d.item_code, target_doc.company).get("default_supplier")
				if frappe.flags.args.default_supplier == default_supplier:
					supplier_items.append(d)
			target_doc.items = supplier_items

		set_missing_values(source, target_doc)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True

		qty = d.ordered_qty or d.received_qty

		return qty < d.stock_qty and child_filter

	def generate_field_map():
		field_map = [
			["name", "material_request_item"],
			["parent", "material_request"],
			["sales_order", "sales_order"],
			["sales_order_item", "sales_order_item"],
			["wip_composite_asset", "wip_composite_asset"],
		]

		if is_subcontracted:
			field_map.extend([["item_code", "fg_item"], ["qty", "fg_item_qty"]])
		else:
			field_map.extend([["uom", "stock_uom"], ["uom", "uom"]])

		return field_map

	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Purchase Order",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": ["in", ["Purchase", "Subcontracting"]],
				},
			},
			"Material Request Item": {
				"doctype": "Purchase Order Item",
				"field_map": generate_field_map(),
				"field_no_map": ["item_code", "item_name", "qty"] if is_subcontracted else ["rate", "price_list_rate"],
				"postprocess": update_item,
				"condition": select_item,
			},
		},
		target_doc,
		postprocess,
		ignore_permissions=True
	)

	doclist.set_onload("load_after_mapping", False)
	if not_return_doclist:
		doclist.save(ignore_permissions=True)
		doclist.submit()
	return doclist

def set_missing_values(source, target_doc):
	if target_doc.doctype == "Purchase Order" and getdate(target_doc.schedule_date) < getdate(nowdate()):
		target_doc.schedule_date = None
	target_doc.run_method("set_missing_values")
	target_doc.run_method("calculate_taxes_and_totals")

def update_item(obj, target, source_parent):
	target.conversion_factor = obj.conversion_factor

	qty = obj.ordered_qty or obj.received_qty
	target.qty = flt(flt(obj.stock_qty) - flt(qty)) / target.conversion_factor
	target.stock_qty = target.qty * target.conversion_factor
	if getdate(target.schedule_date) < getdate(nowdate()):
		target.schedule_date = None

	if target.fg_item:
		target.fg_item_qty = obj.stock_qty
		if sc_bom := get_subcontracting_boms_for_finished_goods(target.fg_item):
			target.item_code = sc_bom.service_item
			target.uom = sc_bom.service_item_uom
			target.conversion_factor = (
				frappe.db.get_value(
					"UOM Conversion Detail",
					{"parent": sc_bom.service_item, "uom": sc_bom.service_item_uom},
					"conversion_factor",
				)
				or 1
			)
			target.qty = target.fg_item_qty * sc_bom.conversion_factor
			target.stock_qty = target.qty * target.conversion_factor

@frappe.whitelist()
def get_work_order_items(material_request):
    """
    Return items with BOM from Material Request
    """

    mr = frappe.get_doc("Material Request", material_request)

    items = []

    for i in mr.items:
        bom = get_default_bom(i.item_code)

        if not bom:
            continue

        items.append(
            {
                "name": i.name,
                "item_code": i.item_code,
                "item_name": i.item_name,
                "description": i.description,
                "bom": bom,
                "warehouse": i.warehouse,
                "pending_qty": i.qty,
                "required_qty": i.qty,
                "material_request_item": i.name,
            }
        )

    return items

@frappe.whitelist()
def make_raw_material_request(items, company, material_request, project=None):

	if isinstance(items, str):
		items = frappe._dict(json.loads(items))

	for item in items.get("items"):
		item["include_exploded_items"] = items.get("include_exploded_items")
		item["ignore_existing_ordered_qty"] = items.get("ignore_existing_ordered_qty")
		item["include_raw_materials_from_sales_order"] = items.get("include_raw_materials_from_sales_order")

	items.update({"company": company, "custom_material_request": material_request})

	item_wh = {}
	for item in items.get("items"):
		if item.get("warehouse"):
			item_wh[item.get("item_code")] = item.get("warehouse")

	raw_materials = get_items_for_material_requests(items)
	if not raw_materials:
		frappe.msgprint(_("Material Request not created, as quantity for Raw Materials already available."))
		return

	new_material_request = frappe.new_doc("Material Request")
	new_material_request.update(
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
		row = new_material_request.append(
			"items",
			{
				"item_code": item.get("item_code"),
				"qty": item.get("quantity"),
				"schedule_date": schedule_date,
				"warehouse": item_wh.get(item.get("main_item_code")) or item.get("warehouse"),
				"custom_material_request": material_request,
				"project": project,
			},
		)

		if not (strip_html(item.get("description")) and strip_html(item_doc.description)):
			row.description = item_doc.item_name or item.get("item_code")

	new_material_request.insert()
	new_material_request.flags.ignore_permissions = 1
	new_material_request.run_method("set_missing_values")
	new_material_request.submit()
	return new_material_request
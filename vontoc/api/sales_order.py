import frappe
from frappe.utils import flt
from erpnext.stock.get_item_details import (
	ItemDetailsCtx,
	get_bin_details,
	get_price_list_rate,
)
from frappe.model.mapper import get_mapped_doc

def sales_order_submitted(self):
    if self.is_internal_customer == 1:
        MR = make_material_request(self.name)
        MR.title = None
        MR.insert(ignore_permissions=True)
        MR.submit()

def make_material_request(source_name, target_doc=None):
	requested_item_qty = get_requested_item_qty(source_name)

	def postprocess(source, target):
		if source.tc_name and frappe.db.get_value("Terms and Conditions", source.tc_name, "buying") != 1:
			target.tc_name = None
			target.terms = None

	def get_remaining_qty(so_item):
		return flt(
			flt(so_item.qty)
			- flt(requested_item_qty.get(so_item.name, {}).get("qty"))
			- max(
				flt(so_item.get("delivered_qty"))
				- flt(requested_item_qty.get(so_item.name, {}).get("received_qty")),
				0,
			)
		)

	def get_remaining_packed_item_qty(so_item):
		delivered_qty = frappe.db.get_value(
			"Sales Order Item", {"name": so_item.parent_detail_docname}, ["delivered_qty"]
		)

		bundle_item_qty = frappe.db.get_value(
			"Product Bundle Item", {"parent": so_item.parent_item, "item_code": so_item.item_code}, ["qty"]
		)

		return flt(
			(
				flt(so_item.qty)
				- flt(requested_item_qty.get(so_item.name, {}).get("qty"))
				- max(
					flt(delivered_qty) * flt(bundle_item_qty)
					- flt(requested_item_qty.get(so_item.name, {}).get("received_qty")),
					0,
				)
			)
			* bundle_item_qty
		)

	def update_item(source, target, source_parent):
		# qty is for packed items, because packed items don't have stock_qty field
		target.project = source_parent.project
		target.qty = (
			get_remaining_packed_item_qty(source)
			if source.parentfield == "packed_items"
			else get_remaining_qty(source)
		)
		target.stock_qty = flt(target.qty) * flt(target.conversion_factor)
		target.actual_qty = get_bin_details(
			target.item_code, target.warehouse, source_parent.company, True
		).get("actual_qty", 0)

		ctx = ItemDetailsCtx(target.as_dict().copy())
		ctx.update(
			{
				"company": source_parent.get("company"),
				"price_list": frappe.db.get_single_value("Buying Settings", "buying_price_list"),
				"currency": source_parent.get("currency"),
				"conversion_rate": source_parent.get("conversion_rate"),
			}
		)

		target.rate = flt(
			get_price_list_rate(ctx, item_doc=frappe.get_cached_doc("Item", target.item_code)).get(
				"price_list_rate"
			)
		)
		target.amount = target.qty * target.rate

	doc = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {"doctype": "Material Request", "validation": {"docstatus": ["=", 1]}},
			"Packed Item": {
				"doctype": "Material Request Item",
				"field_map": {"parent": "sales_order", "uom": "stock_uom", "name": "packed_item"},
				"condition": lambda item: get_remaining_packed_item_qty(item) > 0,
				"postprocess": update_item,
			},
			"Sales Order Item": {
				"doctype": "Material Request Item",
				"field_map": {
					"name": "sales_order_item",
					"parent": "sales_order",
					"delivery_date": "schedule_date",
					"bom_no": "bom_no",
				},
				"condition": lambda item: not frappe.db.exists(
					"Product Bundle", {"name": item.item_code, "disabled": 0}
				)
				and get_remaining_qty(item) > 0,
				"postprocess": update_item,
			},
		},
		target_doc,
		postprocess,
		ignore_permissions=True
	)

	return doc

def get_requested_item_qty(sales_order):
	result = {}
	for d in frappe.db.get_all(
		"Material Request Item",
		filters={"docstatus": 1, "sales_order": sales_order},
		fields=[
			"sales_order_item",
			"packed_item",
			{"SUM": "qty", "as": "qty"},
			{"SUM": "received_qty", "as": "received_qty"},
		],
		group_by="sales_order_item, packed_item",
	):
		result[d.sales_order_item or d.packed_item] = frappe._dict(
			{"qty": d.qty, "received_qty": d.received_qty}
		)

	return result
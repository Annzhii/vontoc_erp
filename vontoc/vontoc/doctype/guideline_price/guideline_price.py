# Copyright (c) 2025, anzhi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from vontoc.utils.todo import close_todo
from vontoc.utils.process_engine import process_flow_engine

class GuidelinePrice(Document):
    pass

@frappe.whitelist()
def map_supplier_quotation_items(sq_name):
    sq = frappe.get_doc("Supplier Quotation", sq_name)
    items = []

    for item in sq.items:
        items.append({
            "item_code": item.item_code,
            "quantity": item.qty,
            "uom": item.uom,
            "supplier_price": item.rate
        })

    return items

@frappe.whitelist()
def rfq_process_step_04(gp):
    #关闭todo
    #close_todo(gp)
    #创建流程记录
    #启动下一步骤
    doc = frappe.get_doc("Guideline Price", gp)
    create_standard_selling(doc)

    to_close =[{
        "doctype":"Guideline Price",
        "docname":gp
    }]

    rfq = doc.rfq
    trace_name = frappe.get_value(
        "Process Flow Trace Doc Item",
        {
            "reference": rfq,
            "_doctype": "Request for Quotation"
        },
        "parent"
    )
    if trace_name:
        process_flow_trace_info = {
            "trace": "close",
            "pf_name": trace_name,
            "ref_doctype": None,
            "ref_docname": None,
            "todo_name": None
        }
        process_flow_engine(to_close = to_close, process_flow_trace_info=process_flow_trace_info)

@frappe.whitelist()
def check_existing_prices(gp):
    doc = frappe.get_doc("Guideline Price", gp)
    existing = []
    for item in doc.items:
        if item.item_code and item.standard_selling_price:
            existing_price = frappe.db.get_value(
                "Item Price",
                {
                    "item_code": item.item_code,
                    "price_list": "Standard Selling"
                },
                "price_list_rate"
            )
            if existing_price:
                existing.append({
                    "item_code": item.item_code,
                    "price": existing_price
                })
    return existing

def create_standard_selling(doc):
    for item in doc.items:
        if item.item_code and item.standard_selling_price:
            exits_item_price = frappe.db.exists("Item Price",{
                "item_code": item.item_code,
                "price_list": "Standard Selling"
            })
            if not exits_item_price:
                item_price = frappe.get_doc({
                    "doctype": "Item Price",
                    "item_code": item.item_code,
                    "price_list": "Standard Selling",
                    "price_list_rate": item.standard_selling_price,
                    "uom": item.uom  # 如果你在子表中有 uom 字段
                })

                item_price.insert(ignore_permissions=True)
# Copyright (c) 2025, anzhi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from vontoc.utils.todo import close_todo
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.utils import get_marked_user

class GuidelinePrice(Document):
    pass
"""
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
"""
@frappe.whitelist()
def send_guideline_price(docname):
    pf_name = get_process_flow_trace_id_by_reference("Guideline Price", [docname])

    to_open = [{
        "doctype": "Guideline Price",
        "docname": docname,
        "user": "Product Pricelist",
        "description": (
            "审核所申请物料的信息是否完整，如果完整，报指导销售价。"
        ),
    }]

    if not pf_name:
        setup_info={
            "trace": "setup",
            "pf_type": "Guideline Price",
            "ref_doctype": "Guideline Price",
            "ref_docname": docname,
            "mark": "1"
        }
        pf_name = process_flow_engine(process_flow_trace_info=setup_info)

        process_flow_trace_info = {
            "pf_name": [pf_name],
            "trace": "add",
            "todo_name": None,
        }

        process_flow_engine(to_open=to_open, process_flow_trace_info=process_flow_trace_info)
        return
    
    process_flow_trace_info = {
        "pf_name": pf_name,
        "trace": "add",
        "todo_name": None,
    }

    to_close = [{"doctype": "Guideline Price", "docname": docname}]

    process_flow_engine(
        to_close=to_close,
        to_open=to_open,
        process_flow_trace_info=process_flow_trace_info,
    )

def submit_guideline_price(self):
    to_close = [
        {
            "doctype": "Guideline Price",
            "docname": self.name
        }
    ]
    
    pf_name = get_process_flow_trace_id_by_reference("Guideline Price", [self.name])

    process_flow_trace_info={
        "pf_name": pf_name,
        "trace": "close",
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, process_flow_trace_info=process_flow_trace_info)

@frappe.whitelist()
def reject_guideline_price(docname):
    pf_name = get_process_flow_trace_id_by_reference("Guideline Price", [docname])
    # pf_name列表中元素只会有1个
    user = get_marked_user (pf_name[0], mark = "1")
    to_close = [
        {
            "doctype": "Guideline Price",
            "docname": docname
        }
    ]
    
    to_open = [
        {
            "doctype": "Guideline Price",
            "docname": docname,
            "user": user,
            "description": "业务员根据驳回意见修改物料信息并重新提交报价申请。",
        }
    ]

    process_flow_trace_info={
        "pf_name": pf_name,
        "trace": "add",
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info=process_flow_trace_info)
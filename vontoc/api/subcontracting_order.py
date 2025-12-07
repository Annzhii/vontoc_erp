import frappe
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference 
from vontoc.utils.process_engine import process_flow_engine

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
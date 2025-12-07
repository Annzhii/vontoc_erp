import frappe
from vontoc.utils.process_engine import process_flow_engine

@frappe.whitelist()
def material_request_submitted (doc):
    if doc.material_request_type == "Purchase":
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



import frappe
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from vontoc.utils.process_engine import process_flow_engine

@frappe.whitelist()
def material_request_submitted (docname):
    process_flow_trace_info={
        "trace": "setup",
        "pf_type": "Purchase",
        "ref_doctype": "Material Request",
        "ref_docname": docname
    }
    pf_name = process_flow_engine(process_flow_trace_info=process_flow_trace_info)

    po_doc = make_purchase_order(docname)
    po_doc.insert()

    to_open= [{
        "doctype": "Purchase Order",
        "docname": po_doc.name,
        "user": "Purchase",
        "description": "请提交采购单",
    }]

    _process_flow_trace_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Purchase Order",
        "ref_docname": po_doc.name,
        "todo_name": None
    }
    process_flow_engine(to_open = to_open, process_flow_trace_info=_process_flow_trace_info)
    
    return f"你已经成功提交了RFQ"

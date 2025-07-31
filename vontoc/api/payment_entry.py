import frappe
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.process_engine import process_flow_engine

@frappe.whitelist()
def payment_entry_verified(doc):
    to_close = [{
        "doctype":"Payment Entry",
        "docname":doc.name
    }]

    references = []

    for ref in doc.references:
        references.append({
            "ref_type": ref.reference_doctype,
            "reference": ref.reference_name
        })

    ref_type = references[0]["ref_type"]
    reference = references[0]["reference"]
    
    pf_name = get_process_flow_trace_id_by_reference(ref_type, reference)

    process_flow_info = {
        "trace": "close",
        "pf_name": pf_name,
        "ref_doctype": None,
        "ref_docname": None,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, process_flow_trace_info= process_flow_info)


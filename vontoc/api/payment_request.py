import frappe
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.process_engine import process_flow_engine
from frappe import _
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_entry

def payment_request_submitted(self):
    #if flt(self.outstanding_amount) > 0:
    entry_dict = make_payment_entry(self.name) 
    if not entry_dict:
        frappe.throw(_("Failed to create Payment Entry"))

    payment_entry = frappe.get_doc(entry_dict)
    payment_entry.insert()                                                
    to_close = [{
        "doctype": "Payment Request",
        'docname': self.name
    }]
    to_open = [{
        "doctype": "Payment Entry",
        "docname": payment_entry.name,
        "user": "Accounts",
        "description": "根据实际收付款情况填写款项单。",
    }]
    pf_name = get_process_flow_trace_id_by_reference(self.reference_doctype, self.reference_name)
    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Payment Entry",
        "ref_docname": payment_entry.name,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)
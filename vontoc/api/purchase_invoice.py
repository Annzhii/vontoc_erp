import frappe
from vontoc.utils.process_engine import process_flow_engine
from frappe.utils import flt
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

def submit_pi(self):
    mr = set()
    for item in self.items:
        if item.material_request:
            mr.add(item.material_request)
    _reference = list(mr)[0]
    pf_name = get_process_flow_trace_id_by_reference("Material Request", _reference)
    

    to_close = [{
        "doctype": "Purchase Invoice",
        'docname': self.name
    }]
    if flt(self.outstanding_amount) > 0:
        payment_request = make_payment_request(
            dt=self.doctype,
            dn=self.name,
            recipient_id=self.supplier,
            #submit_doc=True,  # 是否直接提交
            mute_email=True   # 不发送邮件
        )

        to_open = [{
            "doctype": "Payment Request",
            "docname": payment_request.name,
            "user": "approver",
            "description": "审批付款请求",
        }]
        process_flow_info = {
            "trace": "add",
            "pf_name": pf_name,
            "ref_doctype": "Payment Request",
            "ref_docname": payment_request.name,
            "todo_name": None
        }

        process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

    elif flt(self.outstanding_amount) == 0:
        process_flow_info = {
            "trace": "close",
            "pf_name": pf_name,
            "ref_doctype": None,
            "ref_docname": None,
            "todo_name": None
        }
        process_flow_engine(to_close=to_close, process_flow_trace_info=process_flow_info)

@frappe.whitelist()
def validate_pr(docname):
    doc = frappe.get_doc("Purchase Invoice", docname)
    mr = set()
    for item in doc.items:
        if item.purchase_order:
            mr.add(item.purchase_order)
    _reference = list(mr)[0]
    print (_reference)
    pf_name = get_process_flow_trace_id_by_reference("Purchase Order", _reference)

    to_close = [{
        "doctype": "Purchase Invoice",
        'docname': docname
    }]
    to_open = [{
        "doctype": "Purchase Invoice",
        "docname": docname,
        "user": "Accounts",
        "description": "验证采购发票的金额和供应商提供发票金额是否一致，如一致，提交采购发票",
    }]

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Purchase Invoice",
        "ref_docname": docname,
        "todo_name": None
    }
    
    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

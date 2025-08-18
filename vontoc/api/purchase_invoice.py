import frappe
from vontoc.utils.process_engine import process_flow_engine
from frappe.utils import flt
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

def submmit_pi(self):
    if flt(self.outstanding_amount) > 0:
        payment_request = make_payment_request(
            dt=self.doctype,
            dn=self.name,
            recipient_id=self.supplier,
            #submit_doc=True,  # 是否直接提交
            mute_email=True   # 不发送邮件
        )
    to_close = [{
        "doctype": "Purchase Invoice",
        'docname': self.name
    }]
    to_open = [{
        "doctype": "Payment Request",
        "docname": payment_request.name,
        "user": "approver",
        "description": "审核付款请求",
    }]
    mr = set()
    for item in self.items:
        if item.material_request:
            mr.add(item.material_request)
    _reference = list(mr)[0]
    pf_name = get_process_flow_trace_id_by_reference("Material Request", _reference)
    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Payment Request",
        "ref_docname": payment_request.name,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

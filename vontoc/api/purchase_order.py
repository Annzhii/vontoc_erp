import frappe
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from frappe import _
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

@frappe.whitelist()
def sent_po_for_approval(docname):
    to_close = [{
        "doctype": "Purchase Order",
        'docname': docname
    }]

    to_open = [{
        "doctype": "Purchase Order",
        "docname": docname,
        "user": "approver",
        "description": "审批采购单",
    }]

    def get_first_material_request(po_name):
        po = frappe.get_doc("Purchase Order", po_name)
        for item in po.items:
            if item.material_request:
                return item.material_request
        return None

    _reference = get_first_material_request(docname)
    doctype = "Material Request"
    pf_name = get_process_flow_trace_id_by_reference(doctype, _reference)

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Purchase Order",
        "ref_docname": docname,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

def create_invoice_or_receipt_based_on_terms(self):
    if not self.payment_schedule:
        frappe.msgprint(_('无payment_schedule'))
        return

    has_advance_term = any(
        row.payment_term and "advance" in row.payment_term.strip().lower()
        for row in self.payment_schedule
    )

    if has_advance_term:
        if getattr(self, "custom_deposit_invoice", 0) == 1:
            create_purchase_invoice(self)
        else:
            create_payment_request(self)
    else:
        create_purchase_receipt(self)

def create_purchase_invoice(self):

    pi = make_purchase_invoice(self.name)
    pi.flags.ignore_permissions = True
    pi.insert()

    to_close = [{
        "doctype": "Purchase Order",
        'docname': self.name
    }]

    to_open = [{
        "doctype": "Purchase Invoice",
        "docname": pi.name,
        "user": "Purchase",
        "description": "审核采购发票上面的金额,并让供应商开具相应金额发票",
    }]

    pf_name = get_process_flow_trace_id_by_reference(self.doctype, self.name)

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Purchase Invoice",
        "ref_docname": pi.name,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

def create_payment_request(self):
    pr = make_payment_request(
        dt="Purchase Order",                # 关联单据类型
        dn=self.name,                       # 关联单据名称
        recipient_id=self.supplier,         # 收款对象，这里是供应商
        payment_request_type="Outward",     # 对供应商付款
        mute_email=True                     # 不自动发邮件
    )
    to_close = [{
        "doctype": "Purchase Order",
        'docname': self.name
    }]
    to_open = [{
        "doctype": "Payment Request",
        "docname": pr.name,
        "user": "Purchase",
        "description": "填入正确的收款或付款金额。",
    }]

    pf_name = get_process_flow_trace_id_by_reference(self.doctype, self.name)

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Payment Request",
        "ref_docname": pr.name,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info=process_flow_info)

def create_purchase_receipt(self):

    pr = make_purchase_receipt(self.name)
    pr.flags.ignore_permissions = True
    pr.insert()

    to_close = [{
        "doctype": "Purchase Order",
        'docname': self.name
    }]

    to_open = [{
        "doctype": "Purchase Receipt",
        "docname": pr.name,
        "user": "Purchase",
        "description": "跟进货物交期，并发送收货单。",
    }]

    pf_name = get_process_flow_trace_id_by_reference(self.doctype, self.name)

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Purchase Receipt",
        "ref_docname": pr.name,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

def check_payment_schedule(doc):
    if not doc.payment_schedule:
        frappe.throw("提交采购订单前必须填写付款计划 (Payment Schedule)")
import frappe
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from frappe import _
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

@frappe.whitelist()
def sent_po_for_approval(docname):
    frappe.msgprint("调用成功")
    to_close = [{
        "doctype": "Purchase Order",
        'docname': docname
    }]

    to_open = [{
        "doctype": "Purchase Order",
        "docname": docname,
        "user": "Administrator",
        "description": "请审核采购单",
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
        create_purchase_invoice(self)
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
        "description": "让供应商开具相应发票",
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

    frappe.msgprint(f"自动创建采购发票：<a href='/app/purchase-invoice/{pi.name}'>{pi.name}</a>")

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
        "description": "提交收货单",
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

    frappe.msgprint(f"自动创建采购收货单：<a href='/app/purchase-receipt/{pr.name}'>{pr.name}</a>")
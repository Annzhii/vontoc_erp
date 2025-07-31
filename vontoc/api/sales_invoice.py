import frappe
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.process_engine import process_flow_engine
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

@frappe.whitelist()
def sales_invoice_submitted(docname):
    # 获取 Sales Invoice 文档
    doc = frappe.get_doc("Sales Invoice", docname)

    # 创建 Payment Request（注意使用 keyword arguments）
    payment_request = make_payment_request(
        dt="Sales Invoice",
        dn=docname,
        recipient_id=doc.customer,  # or doc.contact_person if more appropriate
        mute_email=True
    )

    # 插入 Payment Request（非立即提交）
    #payment_request.insert(ignore_permissions=True)

    # 关闭 Sales Invoice 的流程
    to_close = [{
        "doctype": "Sales Invoice",
        'docname': docname
    }]

    # 打开 Payment Request 的新待办
    to_open = [{
        "doctype": "Payment Request",
        "docname": payment_request.name,
        "user": "Accounts",
        "description": "匹配款项",
    }]
    ref_type, reference = get_invoice_source_and_refs(docname)

    pf_name = get_process_flow_trace_id_by_reference(ref_type, reference)

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Payment Request",
        "ref_docname": payment_request.name,
        "todo_name": None
    }

    # 更新流程状态
    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info=process_flow_info)

def get_invoice_source_and_refs(si_name):
    si = frappe.get_doc("Sales Invoice", si_name)

    dn_names = {item.delivery_note for item in si.items if item.delivery_note}
    so_names = {item.sales_order for item in si.items if item.sales_order}

    if dn_names:
        ref_type = "Delivery Note"
        reference = list(dn_names)[0]
    elif so_names:
        ref_type = "Sales Order"
        reference = list(so_names)[0]
    else:
        ref_type = "Manual or Other"
        reference = None

    return ref_type, reference

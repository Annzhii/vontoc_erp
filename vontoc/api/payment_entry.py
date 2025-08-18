import frappe
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.process_engine import process_flow_engine

@frappe.whitelist()
def payment_entry_verified(doc):
    pf_name = get_process_flow_trace_id_by_reference(doc.doctype, doc.name)
    to_close = [{
        "doctype": "Payment Entry",
        "docname": doc.name
    }]

    if not doc.references:
        frappe.throw("Payment Entry 没有关联的参考单据")

    # 取第一个 reference
    ref_type = doc.references[0].reference_doctype
    reference = doc.references[0].reference_name

    # 追溯到 SO / PO
    if ref_type in ["Sales Order", "Purchase Order"]:
        order_type = ref_type
        order_name = reference

    elif ref_type == "Sales Invoice":
        inv = frappe.get_doc("Sales Invoice", reference)
        order_type = "Sales Order"
        order_name = inv.items[0].sales_order if inv.items else None

    elif ref_type == "Purchase Invoice":
        inv = frappe.get_doc("Purchase Invoice", reference)
        order_type = "Purchase Order"
        order_name = inv.items[0].purchase_order if inv.items else None

    else:
        order_type = None
        order_name = None

    if order_type and order_name:
        order_doc = frappe.get_doc(order_type, order_name)
        if ((getattr(order_doc, "per_billed", 0) >= 100 and getattr(order_doc, "per_received", 0) >= 100)or ((order_type == "Sales Order"))):
            # 完全 billed 且 完全received→ 关闭流程
            process_flow_info = {
                "trace": "close",
                "pf_name": pf_name,
                "ref_doctype": None,
                "ref_docname": None,
                "todo_name": None
            }
            process_flow_engine(to_close=to_close, process_flow_trace_info=process_flow_info)

        else:
            # 未完全 billed 或未完全received 且 是付款的
            if doc.payment_type == "Pay" and order_type == "Purchase Order":
                from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
                pr = make_purchase_receipt(order_name)
                pr.flags.ignore_permissions = True
                pr.insert()
                process_flow_info = {
                    "trace": "add",
                    "pf_name": pf_name,
                    "ref_doctype": pr.doctype,
                    "ref_docname": pr.name,
                    "todo_name": None
                }
                to_open = [{
                    "doctype": pr.doctype,
                    "docname": pr.name,
                    "user": "purchase",
                    "description": "跟进货物交期，并发送收货单。",
                }]
                process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info=process_flow_info)




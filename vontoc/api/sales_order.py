import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from vontoc.utils.process_engine import process_flow_engine

@frappe.whitelist()
def create_sales_invoice_or_payment_request(sales_order_name):
    doc = frappe.get_doc("Sales Order", sales_order_name)

    # 判断是否有 'Advance' 类型的 payment_term
    advance_amount = sum(
        row.payment_amount
        for row in doc.payment_schedule
        if row.payment_term and row.payment_term.lower() == "advance"
    )

    if not advance_amount:
        return {"status": "no_advance", "message": "No advance payment term found."}

    if doc.get("custom_deposit_invoice") == 1:
        process_flow_trace_info = {
            "trace": "setup",
            "pf_type": "Advance",
            "ref_doctype": "Sales Order",
            "ref_docname": doc.name,
            "todo_name": None
        }
        pf_name = process_flow_engine(process_flow_trace_info=process_flow_trace_info)

        sales_invoice = make_sales_invoice(sales_order_name)
        sales_invoice.insert(ignore_permissions=True)

        to_open = [{
            "doctype": "Sales Invoice",
            "docname": sales_invoice.name,
            "user": "Sales",
            "description": "请发送Deposit Invoice",
        }]

        _process_flow_trace_info = {
            "trace": "add",
            "pf_name": pf_name,
            "ref_doctype": "Sales Invoice",
            "ref_docname": sales_invoice.name,
            "todo_name": None
        }
        process_flow_engine(to_open=to_open, process_flow_trace_info=_process_flow_trace_info)

        return {
            "status": "sales_invoice_created",
            "invoice_name": sales_invoice.name
        }

    else:
        process_flow_trace_info = {
            "trace": "setup",
            "pf_type": "Advance",
            "ref_doctype": "Sales Order",
            "ref_docname": doc.name,
            "todo_name": None
        }
        pf_name = process_flow_engine(process_flow_trace_info=process_flow_trace_info)

        # 获取或创建 Payment Request
        payment_request = make_payment_request(
            dt="Sales Order",
            dn=doc.name,
            recipient_id=doc.customer,
            payment_request_type="Inward",
            #grand_total=advance_amount,
            # mode_of_payment=frappe.db.get_single_value("Accounts Settings", "default_mode_of_payment"),
            mute_email=True
        )
        #payment_request.insert(ignore_permissions=True)

        to_open = [{
            "doctype": "Payment Request",
            "docname": payment_request.name,
            "user": "Accounts",
            "description": "请处理预付款请求",
        }]
        _process_flow_trace_info = {
            "trace": "add",
            "pf_name": pf_name,
            "ref_doctype": "Payment Request",
            "ref_docname": payment_request.name,
            "todo_name": None
        }
        process_flow_engine(to_open=to_open, process_flow_trace_info=_process_flow_trace_info)

        return {
            "status": "payment_request_created",
            "payment_request_name": payment_request.name
        }

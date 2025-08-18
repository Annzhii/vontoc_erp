import frappe
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from frappe import _

@frappe.whitelist()
def sent_dn_for_approval(docname):
    dn = frappe.get_doc("Delivery Note", docname)
    process_flow_trace_info = {
        "trace": "setup",
        "pf_type": "Delivery",
        "ref_doctype": "Delivery Note",
        "ref_docname": docname,
        "todo_name": None
    }
    pf_name = process_flow_engine(process_flow_trace_info=process_flow_trace_info)

    to_open = [{
        "doctype": "Delivery Note",
        "docname": docname,
        "user": "approver",
        "description": "审批Delivery Note，决定是否允许发货",
    }]

    _process_flow_trace_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Delivery Note",
        "ref_docname": docname,
        "todo_name": None
    }
    process_flow_engine(to_open=to_open, process_flow_trace_info=_process_flow_trace_info)
    
@frappe.whitelist()
def approve_dn(docname):
    dn = frappe.get_doc("Delivery Note", docname)
    to_close = [{
        "doctype": "Delivery Note",
        'docname': docname
    }]
    to_open = [{
        "doctype": "Delivery Note",
        "docname": docname,
        "user": "delivery",
        "description": "联系货代，根据货物数量和装柜方式，制作Packing Slip，并点击安排完成装箱单按钮。",
    }]
    pf_name = get_process_flow_trace_id_by_reference(dn.doctype,docname)
    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Delivery Note",
        "ref_docname": docname,
        "todo_name": None
    }
    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info=process_flow_info)

@frappe.whitelist()
def mark_ready_for_dispatch(docname):
    dn = frappe.get_doc("Delivery Note", docname)

    # 1. 标记完成装箱
    dn.custom_packing_confirmed = 1
    dn.save()
    frappe.db.commit()

    # 2. 准备流程控制
    assigned_user = "stock"
    description = "根据Delivery Note表单上的数量完成货物出库"

    to_close = [{
        "doctype": "Delivery Note",
        "docname": docname
    }]

    to_open = [{
        "doctype": "Delivery Note",
        "docname": docname,
        "user": assigned_user,
        "description": description
    }]

    pf_name = get_process_flow_trace_id_by_reference(dn.doctype, docname)

    # 4. 构建 trace 信息
    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Delivery Note",
        "ref_docname": docname,
        "todo_name": None
    }

    # 5. 推动流程引擎
    process_flow_engine(
        to_close=to_close,
        to_open=to_open,
        process_flow_trace_info=process_flow_info
    )

def delivery_note_submitted(dn):
    # 如果是退货单，执行另外一个逻辑
    if dn.is_return == 1:
        return handle_return_delivery_note(dn)

    # 正常出库流程
    assigned_user = "delivery"
    description = "判定实际出货数量是否和出库数量一致，如一致，完成出货，如不一致，确认数量差，完成退货入库"

    to_close = [{
        "doctype": "Delivery Note",
        "docname": dn.name
    }]

    to_open = [{
        "doctype": "Delivery Note",
        "docname": dn.name,
        "user": assigned_user,
        "description": description
    }]

    pf_name = get_process_flow_trace_id_by_reference(dn.doctype, dn.name)

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Delivery Note",
        "ref_docname": dn.name,
        "todo_name": None
    }

    process_flow_engine(
        to_close=to_close,
        to_open=to_open,
        process_flow_trace_info=process_flow_info
    )

def handle_return_delivery_note(self):
    delivery_dispatched(self.return_against, from_return=1)

@frappe.whitelist()
def delivery_dispatched(docname, from_return = None):
    dn = frappe.get_doc("Delivery Note", docname)

    # 1. 检查是否所有关联的 Packing Slip 都已提交
    packing_slips = frappe.get_all(
        "Packing Slip",
        filters={"delivery_note": docname},
        fields=["name", "docstatus"]
    )

    unsubmitted = [ps.name for ps in packing_slips if ps.docstatus != 1]
    if unsubmitted:
        msg = _("以下 Packing Slip 尚未提交：\n") + "\n".join(unsubmitted)
        frappe.throw(msg)

    # 2. 标记 custom_delivery_dispatched 字段
    dn.db_set("custom_delivery_dispatched", 1, update_modified=False)

    # 3. 尝试创建销售发票
    created_si = None
    if not is_fully_billed(dn):
        created_si = make_sales_invoice_from_dn(docname)
        #frappe.msgprint(_("已创建销售发票: ") + created_si.name)

    # 4. 处理流程跟踪
    pf_name = get_process_flow_trace_id_by_reference("Delivery Note", docname)
    to_close_docname = [r["name"] for r in find_returns_for_delivery_note(docname)] if from_return else [docname]
    to_close = [{
        "doctype": "Delivery Note",
        "docname": to_close_docname[0]
    }]

    to_open = []
    trace_action = "add" if created_si else "close"

    if created_si:
        to_open.append({
            "doctype": "Sales Invoice",
            "docname": created_si.name,
            "user": "sales",
            "description": "通知客户在发票时间内付清尾款，"
        })

    process_flow_info = {
        "trace": trace_action,
        "pf_name": pf_name,
        "ref_doctype": created_si.doctype if created_si else "Delivery Note",
        "ref_docname": created_si.name if created_si else docname,
        "todo_name": None
    }

    process_flow_engine(
        to_close=to_close,
        to_open=to_open,
        process_flow_trace_info=process_flow_info
    )

    return created_si.name if created_si else None


def is_fully_billed(dn):
    billed_amt = dn.get("billed_amount") or 0
    total_amt = dn.get("rounded_total") or dn.get("grand_total") or 0
    return billed_amt >= total_amt

def make_sales_invoice_from_dn(delivery_note_name):
    from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

    sales_invoice = make_sales_invoice(delivery_note_name)
    sales_invoice.insert()
    #sales_invoice.submit()
    return sales_invoice

def find_returns_for_delivery_note(docname):
    return_notes = frappe.get_all(
        "Delivery Note",
        filters={
            "return_against": docname,
            "is_return": 1
        },
        fields=["name", "posting_date", "customer"]
    )
    return return_notes


@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Delivery Note", source_name, target_doc)

@frappe.whitelist()
def require_return(docname):
    dn = frappe.get_doc("Delivery Note", docname)
    dn.return_against
    to_close = [{
        "doctype": "Delivery Note",
        'docname': dn.return_against
    }]
    to_open = [{
        "doctype": "Delivery Note",
        "docname": docname,
        "user": "stock",
        "description": "验证Delivery Note上的数量和实际退货数量是否一致",
    }]
    pf_name = get_process_flow_trace_id_by_reference("Delivery Note", dn.return_against)
    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Delivery Note",
        "ref_docname": dn.return_against,
        "todo_name": None
    }
    process_flow_engine(
        to_close=to_close,
        to_open=to_open,
        process_flow_trace_info=process_flow_info
    )
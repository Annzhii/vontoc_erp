import frappe
from frappe import _
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.utils import get_marked_user

def check_delivery_notes_submitted(self):
    # 假设 Shipment 有 child table "shipment_details"，里面有字段 "delivery_note"
    unsubmitted_dn = []

    for row in self.get("shipment_delivery_note"):
        dn_name = row.delivery_note
        if dn_name:
            dn_doc = frappe.get_doc("Delivery Note", dn_name)
            if dn_doc.docstatus != 1:  # 1 = submitted
                unsubmitted_dn.append(dn_name)

    if unsubmitted_dn:
        # 阻止提交，并弹提示
        frappe.throw(
            _("All linked Delivery Notes must be submitted before submitting Shipment. "
                "Unsubmitted Delivery Notes: {0}").format(", ".join(unsubmitted_dn))
        )

@frappe.whitelist()
def send_shipment(docname):
    pf_name = get_process_flow_trace_id_by_reference("Shipment", [docname])

    # --- 通用的 to_open 数据 ---
    to_open = [{
        "doctype": "Shipment",
        "docname": docname,
        "user": "Documentation Clerk",
        "description": (
            "审核出货单信息是否完整，如果完整，联系货代安排订舱。"
        ),
    }]

    if not pf_name:
        setup_info = {
            "trace": "setup",
            "pf_type": "Shipment",
            "ref_doctype": "Shipment",
            "ref_docname": docname,
            "mark": "1"
        }
        pf_name = process_flow_engine(process_flow_trace_info=setup_info)

        process_flow_trace_info = {
            "pf_name": [pf_name],
            "trace": "add",
            "todo_name": None,
        }

        process_flow_engine(to_open=to_open, process_flow_trace_info=process_flow_trace_info)
        return
    
    process_flow_trace_info = {
        "pf_name": pf_name,
        "trace": "add",
        "todo_name": None,
    }

    to_close = [{"doctype": "Shipment", "docname": docname}]

    process_flow_engine(
        to_close=to_close,
        to_open=to_open,
        process_flow_trace_info=process_flow_trace_info,
    )

@frappe.whitelist()
def confirm_booking_of_shipment(docname):
    to_close = [
        {
            "doctype": "Shipment",
            "docname": docname
        }
    ]

    to_open = [{
        "doctype": "Shipment",
        "docname": docname,
        "user": "Accounts Manager",
        "description": (
            "审核发货单中货物的款项是否收齐。"
        ),
    }]

    pf_name = get_process_flow_trace_id_by_reference("Shipment", [docname])

    process_flow_trace_info={
        "pf_name": pf_name,
        "trace": "add",
        "todo_name": None
    }

    process_flow_engine(to_open = to_open, to_close=to_close, process_flow_trace_info=process_flow_trace_info)

@frappe.whitelist()
def payment_collected_in_full_or_approved(docname):
    to_close = [
        {
            "doctype": "Shipment",
            "docname": docname
        }
    ]

    to_open = [{
        "doctype": "Shipment",
        "docname": docname,
        "user": "Stock Manager",
        "description": (
            "根据发货单里的货物类型和数量，完成出库。"
        ),
    }]

    pf_name = get_process_flow_trace_id_by_reference("Shipment", [docname])

    process_flow_trace_info={
        "pf_name": pf_name,
        "trace": "add",
        "todo_name": None
    }

    process_flow_engine(to_open = to_open, to_close=to_close, process_flow_trace_info=process_flow_trace_info)

    # 把所有的DN标记为verified，阻止已经核销的SI记录变更
    shipment = frappe.get_doc("Shipment", docname)
    for row in shipment.get("shipment_delivery_note"):
        dn_name = row.delivery_note
        if dn_name:
            dn_doc = frappe.get_doc("Delivery Note", dn_name)
            dn_doc.custom_verified = 1
            if dn_doc.custom_payment_status != "Full Allocated":
                dn_doc.custom_allow_shipment_before_full_payment = 1
        dn_doc.save()

@frappe.whitelist()
def payment_partially_collected(docname):
    to_close = [
        {
            "doctype": "Shipment",
            "docname": docname
        }
    ]

    to_open = [{
        "doctype": "Shipment",
        "docname": docname,
        "user": "Sales Master Manager",
        "description": (
            "核对收货单中未收齐金额，决定是否允许款项结清前放行出货。"
        ),
    }]

    pf_name = get_process_flow_trace_id_by_reference("Shipment", [docname])

    process_flow_trace_info={
        "pf_name": pf_name,
        "trace": "add",
        "todo_name": None
    }

    process_flow_engine(to_open = to_open, to_close=to_close, process_flow_trace_info=process_flow_trace_info)

@frappe.whitelist()
def outbound(docname):
    to_close = [
        {
            "doctype": "Shipment",
            "docname": docname
        }
    ]

    to_open = [{
        "doctype": "Shipment",
        "docname": docname,
        "user": "Documentation Clerk",
        "description": (
            "货物被提走后提交出运单。"
        ),
    }]

    pf_name = get_process_flow_trace_id_by_reference("Shipment", [docname])

    process_flow_trace_info={
        "pf_name": pf_name,
        "trace": "add",
        "todo_name": None
    }

    process_flow_engine(to_open = to_open, to_close=to_close, process_flow_trace_info=process_flow_trace_info)

@frappe.whitelist()
def dispatch(docname):
    to_close = [
        {
            "doctype": "Shipment",
            "docname": docname
        }
    ]

    pf_name = get_process_flow_trace_id_by_reference("Shipment", [docname])

    process_flow_trace_info={
        "pf_name": pf_name,
        "trace": "close",
        "todo_name": None
    }

    process_flow_engine( to_close=to_close, process_flow_trace_info=process_flow_trace_info)

@frappe.whitelist()
def reject(docname):
    pf_name = get_process_flow_trace_id_by_reference("Shipment", [docname])
    user = get_marked_user (pf_name[0], mark = "1")
    to_close = [
        {
            "doctype": "Shipment",
            "docname": docname
        }
    ]

    to_open = [{
        "doctype": "Shipment",
        "docname": docname,
        "user": user,
        "description": (
            "业务员根据驳回意见修改出运单并重新提交申请。"
        ),
    }]

    process_flow_trace_info={
        "pf_name": pf_name,
        "trace": "add",
        "todo_name": None
    }

    process_flow_engine(to_open = to_open, to_close=to_close, process_flow_trace_info=process_flow_trace_info)
import frappe
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.utils import get_marked_user

def validate_sales_temporary_item(doc):
    user = frappe.session.user
    unrestricted_roles = ["Administrator", "Item Manager"]

    if user == "Administrator":
        return
    
    roles = frappe.get_roles(user)
    if any(role in roles for role in unrestricted_roles):
        return

    if doc.item_group != "临时物料":
        frappe.throw("你只能创建类型为『临时物料』的物料。请调整后再保存。")

@frappe.whitelist()
def send_item_for_approval(docname):
    pf_name = get_process_flow_trace_id_by_reference("Item", [docname])

    # --- 通用的 to_open 数据 ---
    to_open = [{
        "doctype": "Item",
        "docname": docname,
        "user": "Item Manager",
        "description": (
            "审核所申请物料是否合理，如果合理，设置正确的物料分类并批准申请。"
        ),
    }]

    if not pf_name:
        setup_info = {
            "trace": "setup",
            "pf_type": "Item",
            "ref_doctype": "Item",
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

    to_close = [{"doctype": "Item", "docname": docname}]

    process_flow_engine(
        to_close=to_close,
        to_open=to_open,
        process_flow_trace_info=process_flow_trace_info,
    )

@frappe.whitelist()
def approve_item(docname):
    to_close = [
        {
            "doctype": "Item",
            "docname": docname
        }
    ]
    
    pf_name = get_process_flow_trace_id_by_reference("Item", [docname])

    process_flow_trace_info={
        "pf_name": pf_name,
        "trace": "close",
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, process_flow_trace_info=process_flow_trace_info)

@frappe.whitelist()
def reject_item(docname):
    pf_name = get_process_flow_trace_id_by_reference("Item", [docname])
    # pf_name列表中元素只会有1个
    user = get_marked_user (pf_name[0], mark = "1")
    frappe.msgprint(str(user))
    to_close = [
        {
            "doctype": "Item",
            "docname": docname
        }
    ]
    
    to_open = [
        {
            "doctype": "Item",
            "docname": docname,
            "user": user,
            "description": "申请人根据驳回意见修改物料信息并重新提交申请。",
        }
    ]

    process_flow_trace_info={
        "pf_name": pf_name,
        "trace": "add",
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info=process_flow_trace_info)
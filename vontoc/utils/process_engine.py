from vontoc.utils.todo import set_todo, close_todo
from vontoc.utils.processflow import setup_pf_trace, add_pf_trace, close_pf_trace

import frappe

def process_flow_engine(to_close=None, to_open=None, process_flow_trace_info=None):
    """
    统一流程处理函数：
    - 关闭 ToDo
    - 设置 ToDo
    - 处理 Process Flow Trace
    """

    # 关闭 ToDo：to_close 是 list，每项应为 dict：{"doctype": ..., "docname": ...}
    if to_close:
        for item in to_close:
            #doctype = item.get("doctype")
            docname = item.get("docname")
            if docname:
                close_todo(docname)

    # 设置 ToDo：to_setup 是 list，每项应为 dict：{"doctype": ..., "docname": ..., "user": ..., "description": ...}
    if to_open:
        for item in to_open:
            doctype = item.get("doctype")
            docname = item.get("docname")
            user = item.get("user")
            description = item.get("description")
            if doctype and docname and user and description:
                created_todos = set_todo(doctype, docname, user, description)
                process_flow_trace_info["todo_name"] = created_todos

    # 处理流程追踪（trace）
    if not process_flow_trace_info:
        frappe.throw("process_flow_trace_info is required.")

    trace_action = process_flow_trace_info.get("trace")

    if trace_action == "setup":
        pf_name = setup_pf_trace(process_flow_trace_info)
        frappe.msgprint(f"流程启动")
        return pf_name
    elif trace_action == "add":
        add_pf_trace(process_flow_trace_info)
    elif trace_action == "close":
        close_pf_trace(process_flow_trace_info)

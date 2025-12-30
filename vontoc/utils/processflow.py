import frappe
from frappe.utils import now_datetime

def setup_pf_trace(process_flow_trace_info):

    pf_type = process_flow_trace_info.get("pf_type")
    ref_doctype = process_flow_trace_info.get("ref_doctype")
    ref_docname = process_flow_trace_info.get("ref_docname")
    mark = process_flow_trace_info.get("mark")

    pf_trace = frappe.new_doc("Process Flow Trace")
    pf_trace.process_flow_type = pf_type
    
    pf_type_map = {
        "RFQ": "申请人提交RFQ",
        "Purchase": "申请人提交物料申请单",
        "Shipment": "业务员提交出运单",
        "Item": "申请人提交新物料创建申请",
    }
    description = pf_type_map.get(pf_type, pf_type)

    current_time = now_datetime()
    pf_trace.append("process_flow_trace_step", {
        "start_time": current_time,
        "end_time":current_time,
        "description": description,
        "finished_by": frappe.session.user,
        "mark": mark
    })

    # 添加子表：Process Flow Trace Doc Item
    pf_trace.append("process_flow_trace_reference", {
        "_doctype": ref_doctype,
        "reference": ref_docname
    })

    # 提交文档
    pf_trace.insert(ignore_permissions=True)
    frappe.db.commit()

    return pf_trace.name


def add_pf_trace(process_flow_trace_info):
    pf_names = process_flow_trace_info.get("pf_name")
    todo_name = process_flow_trace_info.get("todo_name")
    ref_doctype = process_flow_trace_info.get("ref_doctype")
    ref_docname = process_flow_trace_info.get("ref_docname")
    multi_ref_doc = process_flow_trace_info.get("multi_ref_doc")  # 新增参数
    mark = process_flow_trace_info.get("mark")
    for pf_name in pf_names:
    # 获取已存在的 Process Flow Trace 文档
        pf_trace = frappe.get_doc("Process Flow Trace", pf_name)

        # 添加子表：Process Flow Trace Step
        for _todo_name in todo_name or []:
            todo = frappe.get_doc("ToDo", _todo_name)
            pf_trace.append("process_flow_trace_step", {
                "linked_todo": todo.name,
                "start_time": todo.creation,
                "description": todo.description,
                "allocated_to": todo.allocated_to,
                "mark": mark
            })


        # 添加子表：Process Flow Trace Reference
        if multi_ref_doc:
            for ref in multi_ref_doc:
                ref_dt = ref.get("ref_doctype")
                ref_dn = ref.get("ref_docname")

                exists = any(
                    r._doctype == ref_dt and r.reference == ref_dn
                    for r in pf_trace.process_flow_trace_reference
                )
                if not exists:
                    pf_trace.append("process_flow_trace_reference", {
                        "_doctype": ref_dt,
                        "reference": ref_dn
                    })

        elif ref_doctype and ref_docname:
            exists = any(
                r._doctype == ref_doctype and r.reference == ref_docname
                for r in pf_trace.process_flow_trace_reference
            )
            if not exists:
                pf_trace.append("process_flow_trace_reference", {
                    "_doctype": ref_doctype,
                    "reference": ref_docname
                })

        # 保存更改
        pf_trace.save(ignore_permissions=True)
        frappe.db.commit()

    return pf_trace.name

def close_pf_trace(process_flow_trace_info):
    pf_names = process_flow_trace_info.get("pf_name")
    for pf_name in pf_names:
        pf_trace = frappe.get_doc("Process Flow Trace", pf_name)
        pf_trace.process_flow_status = "Closed"
        pf_trace.save(ignore_permissions=True)
        frappe.db.commit()

def get_process_flow_trace_id_by_reference(doctype, docnames):
    all_results = []
    #表单和流程多对多
    for docname in docnames:
        results = frappe.get_all(
            "Process Flow Trace Doc Item",
            filters={
                "_doctype": doctype,
                "reference": docname
            },
            fields=["parent"],
        )
        all_results.extend(results)

    return list(set(r.get('parent') for r in all_results if r.get('parent')))

def update_process_flow_trace(todo):
    """
    在 Process Flow Trace Steps 里找到 linked_todo = todo.name 的记录，
    把 end_time 更新为 todo.modified（即关闭时间）
    """
    # 只在 ToDo 已关闭时更新
    if todo.status != "Closed":
        return

    step_names = frappe.get_all(
        "Process Flow Trace Steps",
        filters= {"linked_todo": todo.name},
        fields = {"name"}
    )
    for step_name in step_names:
        if step_name:
            frappe.db.set_value(
                "Process Flow Trace Steps",
                step_name,
                {
                    "end_time": todo.modified,
                    "finished_by": frappe.session.user
                }
            )
            frappe.db.commit()

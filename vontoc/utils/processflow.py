import frappe

def setup_pf_trace(process_flow_trace_info):

    pf_type = process_flow_trace_info.get("pf_type")
    ref_doctype = process_flow_trace_info.get("ref_doctype")
    ref_docname = process_flow_trace_info.get("ref_docname")

    # 创建 Process Flow Trace 主文档
    pf_trace = frappe.new_doc("Process Flow Trace")
    pf_trace.process_flow_type = pf_type

    # 添加子表：Process Flow Trace Item
    pf_trace.append("process_flow_trace_step", {

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
    pf_name = process_flow_trace_info.get("pf_name")
    todo_name = process_flow_trace_info.get("todo_name")
    ref_doctype = process_flow_trace_info.get("ref_doctype")
    ref_docname = process_flow_trace_info.get("ref_docname")
    multi_ref_doc = process_flow_trace_info.get("multi_ref_doc")  # 新增参数

    # 获取已存在的 Process Flow Trace 文档
    pf_trace = frappe.get_doc("Process Flow Trace", pf_name)

    # 添加子表：Process Flow Trace Step
    for todo in todo_name or []:
        pf_trace.append("process_flow_trace_step", {
            "linked_todo": todo
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
    pf_name = process_flow_trace_info.get("pf_name")
    pf_trace = frappe.get_doc("Process Flow Trace", pf_name)
    pf_trace.process_flow_status = "Closed"
    pf_trace.save(ignore_permissions=True)
    frappe.db.commit()

def get_process_flow_trace_id_by_reference(doctype, docname):
    result = frappe.get_all(
        "Process Flow Trace Doc Item",
        filters={
            "_doctype": doctype,
            "reference": docname
        },
        fields=["parent"],
        limit=1
    )
    return result[0].parent if result else None
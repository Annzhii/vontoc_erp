import frappe
from vontoc.utils.utils import get_users_by_profile_or_role
from vontoc.utils.processflow import update_process_flow_trace

def set_todo(doctype, docname, user, description):
    # 获取根据用户角色或配置的用户列表
    users = get_users_by_profile_or_role(user)
    
    # 获取对应文档
    ref_doc = frappe.get_doc(doctype, docname)
    created_todos = []

    for _user in users:
        # 检查是否已经存在相同的 ToDo
        existing_todo = frappe.get_all(
            "ToDo",
            filters={
                'reference_type': doctype,
                'reference_name': ref_doc.name,
                'allocated_to': _user.name,
                'description': description,
                'status': 'Open'  # 如果要排除已经完成的 ToDo，也可以加这个条件
            },
            fields=["name"]
        )
        
        if not existing_todo:
            # 如果没有找到重复的 ToDo，创建一个新的 ToDo
            todo = frappe.get_doc({
                'doctype': 'ToDo',
                'description': f'{description}',
                'reference_type': doctype,
                'reference_name': ref_doc.name,
                'assigned_by': frappe.session.user,
                'owner': _user.name,
                'allocated_to': _user.name,
                'status': 'Open',
                # 可以设置截止日期等字段，比如:
                # 'date': frappe.utils.add_days(frappe.utils.nowdate(), 3)
            })
            todo.insert(ignore_permissions=True)
            created_todos.append(todo.name)
        else: created_todos.append(existing_todo[0].name)
    
    return created_todos


def close_todo(doc_name):
    todos = frappe.get_all("ToDo", 
        filters={"reference_name": doc_name, "status": ["!=", "Closed"]},
        fields=["name"]
    )

    for todo in todos:
        todo_doc = frappe.get_doc("ToDo", todo.name)
        todo_doc.status = "Closed"
        todo_doc.save(ignore_permissions=True)
        update_process_flow_trace(todo_doc)
        frappe.msgprint(f"任务完成")
    frappe.db.commit()
import frappe

def set_todo(doctype, docname, user_profile, description):
    _users = frappe.get_all('User',
        filters={
            'role_profile_name': user_profile,
            'enabled': 1
        },
        fields=['name', 'full_name', 'email']
    )
    if not _users:
        frappe.throw(f"没有找到任何拥有 {user_profile} 角色的用户")
    
    ref_doc = frappe.get_doc(doctype, docname)
    created_todos = []

    for user in _users:
        todo = frappe.get_doc({
            'doctype': 'ToDo',
            'description': f'{description}',
            'reference_type': doctype,
            'reference_name': ref_doc.name,
            'assigned_by': frappe.session.user,
            'owner': user.parent,
            'allocated_to': user.email,
            'status': 'Open',
            # 可以设置截止日期等字段，比如:
            # 'date': frappe.utils.add_days(frappe.utils.nowdate(), 3)
        })
        todo.insert(ignore_permissions=True)
        created_todos.append(todo.name)
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

    frappe.db.commit()
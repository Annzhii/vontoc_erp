import frappe

def get_permission_query_conditions(user):
    if not user: user = frappe.session.user
    if user == "Administrator":
        return None
    return f"""(`tabToDo`.`allocated_to` = '{user}')"""
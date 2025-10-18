import frappe
## 后面限制人员只能创建零时物料
def validate_sales_temporary_item(doc, method):
    """Sales 角色只能创建临时物料"""
    user = frappe.session.user
    if user == "Administrator":
        return  # 管理员不受限制

    # 检查当前用户角色
    roles = frappe.get_roles(user)
    if "Sales User" in roles or "Sales Representative" in roles:
        # 校验 item group
        if doc.item_group != "临时物料":
            frappe.throw("销售人员只能创建属于『Temporary』分组的物料，请调整 Item Group 后再保存。")
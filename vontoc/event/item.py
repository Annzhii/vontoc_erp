import frappe
from frappe.model.naming import make_autoname

def get_series_from_naming_rule(doctype, doc):
    """兼容 v15 的 Naming Rule 解析"""
    rules = frappe.get_all(
        "Document Naming Rule",
        filters={"document_type": doctype},
        fields=["name", "priority", "prefix", "prefix_digits"]
    )

    if not rules:
        return None

    # 简单按优先级选择规则
    rules = sorted(rules, key=lambda x: x.priority or 0, reverse=True)

    for r in rules:
        # 如果有条件，可以在这里扩展逻辑
        return f"{r.prefix}.{'#'*r.prefix_digits}"

    return None

def auto_rename_on_group_change(doc, method):
    """Item Group 改变时自动生成 item_code"""
    if doc.flags.in_insert:
        return

    old_group = frappe.db.get_value("Item", doc.name, "item_group")
    if not old_group or old_group == doc.item_group:
        return

    series = get_series_from_naming_rule("Item", doc=doc)
    if not series:
        frappe.msgprint(f"未找到适用的命名规则，保持原编码")
        return

    new_code = make_autoname(series, doc=doc)
    if new_code != doc.name:
        frappe.rename_doc("Item", doc.name, new_code, force=True, merge=False)
        doc.item_code = new_code
        doc.name = new_code
        frappe.msgprint(f"Item Group 从 {old_group} 改为 {doc.item_group}，系统自动更新编码为 {new_code}")

import frappe

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

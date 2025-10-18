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
        if check_rule_conditions_match(r["name"], doc.item_group):
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


def check_rule_conditions_match(rule_name, item_group):
    """检查命名规则的 conditions 表中是否有匹配的 value"""
    # 查询 Document Naming Rule 的 conditions 子表
    conditions = frappe.get_all("Document Naming Rule Condition",
        filters={"parent": rule_name},
        fields=["field", "condition", "value"]
    )
    
    # 如果没有条件，则默认匹配
    if not conditions:
        return True
    
    # 检查所有条件是否匹配
    for condition in conditions:
        if condition.field == "item_group" and condition.condition == "=":
            if condition.value == item_group:
                return True
    
    return False
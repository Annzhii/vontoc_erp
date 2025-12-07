import frappe
from frappe.utils import flt

@frappe.whitelist()
#前端JS调用
def get_user_profile_name():
    user = frappe.get_doc("User", frappe.session.user)
    return user.get("role_profile_name")  # 可能返回 None

def get_users_by_profile_or_role(user: str):
    """优先通过 User Profile 查找用户，如果没有则通过 Role 查找用户。
    在生产模式下自动排除 Administrator，在开发模式下返回 Administrator。
    """

    # 判断是否为生产模式
    is_production = not frappe.conf.get("developer_mode")
    
    # 公共过滤条件
    base_filters = {"enabled": 1}
    
    # 如果是开发模式，直接返回 Administrator 用户
    if not is_production:
        return frappe.get_all(
            "User",
            filters={**base_filters, "name": "Administrator"},
            fields=["name", "full_name", "email"],
        )
    
    # 如果是生产模式，排除 Administrator 用户
    base_filters["name"] = ("!=", "Administrator")

    # 1. 先按 User email 匹配
    users = frappe.get_all(
        "User",
        filters={**base_filters, "email": user},
        fields=["name", "full_name", "email"],
    )

    # 2. 如果没有 → 再按 Role 匹配
    if not users:
        enabled_users = frappe.get_all("User", filters=base_filters, pluck="name")

        if enabled_users:
            role_users = frappe.get_all(
                "Has Role",
                filters={"role": user, "parent": ("in", enabled_users)},
                pluck="parent",
            )

            if role_users:
                users = frappe.get_all(
                    "User",
                    filters={
                        **base_filters,
                        "name": ("in", role_users),
                    },
                    fields=["name", "full_name", "email"],
                )

    # 3. 如果还是没有 → 抛异常
    if not users:
        frappe.throw(f"没有找到任何拥有 {user} 角色配置 或 角色的用户")

    return users

def is_source_fully_generated(links):
    """
    通用判断：source_doc 是否在 target_doctype 中全部生成完毕（按数量判断）
    
    links 示例：
    {
        "source_doc": {"doctype": "Material Request", "docname": "MAT-REQ-2025-0001"},
        "generated_doc": {"doctype": "Purchase Order", "field": "material_request"}
    }
    """
    source = links.get("source_doc", {})
    generated = links.get("generated_doc", {})

    source_doctype = source["doctype"]
    source_name = source["docname"]
    target_doctype = generated["doctype"]
    link_field = generated["field"]        # 如 "material_request"

    # 目标表
    target_item_table = f"tab{target_doctype} Item"
    target_table = f"tab{target_doctype}"

    # 获取源单
    source_doc = frappe.get_doc(source_doctype, source_name)
    if not hasattr(source_doc, "items"):
        frappe.throw(f"{source_doctype} 没有 items 子表，无法比较生成情况")

    # 遍历源单的每一行 item
    for item in source_doc.items:
        source_item_id = item.name                  # 源单子表行唯一 ID
        source_qty = flt(item.qty)                  # 源单行数量

        # 查询该 item 在所有 target_doc 中已生成的数量
        ordered_data = frappe.db.sql(f"""
            SELECT SUM(ti.qty) AS generated_qty
            FROM `{target_item_table}` ti
            INNER JOIN `{target_table}` t ON ti.parent = t.name
            WHERE ti.{link_field} = %s
            AND ti.{link_field}_item = %s
            AND t.docstatus != 2
        """, (source_name, source_item_id), as_dict=True)

        generated_qty = flt(ordered_data[0].generated_qty or 0)

        # 只要一个 item 没生成完 → 全部未完成
        if generated_qty < source_qty:
            return False

    # 全部 item 数量都达到或超过 → 完全生成
    return True

def get_suppliers_warehouse_name(company=None):
    if not company:
        company = frappe.defaults.get_user_default("company")
    company_abbr = frappe.get_value("Company", company, "abbr")
    return f"Suppliers - {company_abbr}"

def if_full_received(mr):
    doc_mr = frappe.get_doc("Material Request", mr)

    if doc_mr.status != "Received":
        return False

    linked_sub_pos = get_linked_sub_pos(doc_mr.name)
    for linked_sub_po_name in linked_sub_pos:
        sub_po_doc = frappe.get_doc("Subcontracting Order", linked_sub_po_name)
        if sub_po_doc.status != "Completed":
            return False

    return True

def get_linked_sub_pos(mr):
    # 先找所有 subcontracted PO
    linked_sub_pos = frappe.get_all(
        "Purchase Order",
        filters={
            "material_request": mr,
            "is_subcontracted": 1
        },
        pluck="name"
    )

    # 用 set 保存所有 SO
    linked_subcontracting_orders = set()

    for po in linked_sub_pos:
        # 找到当前 PO 的所有 Subcontracting Order
        sub_orders = frappe.get_all(
            "Subcontracting Order",
            filters={"purchase_order": po},
            pluck="name"
        )

        for so in sub_orders:
            linked_subcontracting_orders.add(so)

    return list(linked_subcontracting_orders)

def get_marked_user(pf_name, mark):
    allocated_users = frappe.get_all(
        "Process Flow Trace Steps",
        filters={"parent": pf_name, "mark": mark},
        fields=["allocated_to", "finished_by"]
    )
    allocated_to = allocated_users[0].get('allocated_to')
    finished_by = allocated_users[0].get('finished_by')
    if finished_by:
        return finished_by
    elif allocated_to:
        return allocated_to
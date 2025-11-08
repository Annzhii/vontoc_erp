import frappe
from frappe.utils import flt

@frappe.whitelist()
#前端JS调用
def get_user_profile_name():
    user = frappe.get_doc("User", frappe.session.user)
    return user.get("role_profile_name")  # 可能返回 None

def get_users_by_profile_or_role(user: str):
    """优先通过 User Profile 查找用户，如果没有则通过 Role 查找用户。"""

    # 1. 先按 User Profile 匹配
    users = frappe.get_all(
        'User',
        filters={
            'role_profile_name': user,
            'enabled': 1
        },
        fields=['name', 'full_name', 'email']
    )

    # 2. 如果没有 → 再按 Role 匹配
    if not users:
        # 先拿所有 enabled 用户
        enabled_users = frappe.get_all(
            'User',
            filters={'enabled': 1},
            pluck='name'
        )

        if enabled_users:
            # 从 Has Role 里找拥有这个角色的用户
            role_users = frappe.get_all(
                'Has Role',
                filters={'role': user, 'parent': ('in', enabled_users)},
                pluck='parent'
            )

            if role_users:
                users = frappe.get_all(
                    'User',
                    filters={'name': ('in', role_users), 'enabled': 1},
                    fields=['name', 'full_name', 'email']
                )

    # 3. 如果还是没有 → 抛异常
    if not users:
        frappe.throw(f"没有找到任何拥有 {user} 角色配置 或 角色的用户")

    return users

def mark_inspection_confirmed(docname):
    doc = frappe.get_doc("Purchase Receipt", docname)
    doc.db_set("custom_inspection_confirmed", 1)  # ✅ 强制写入数据库，不依赖 save()

def get_linked_po(purchase_receipt_name):
    doc = frappe.get_doc("Purchase Receipt", purchase_receipt_name)
    po = set()
    for item in doc.items:
        if item.purchase_order:
            po.add(item.purchase_order)
    _reference = list(po)[0]
    return _reference

def get_received_qty(po_name, item_code):
    total_received = frappe.db.sql("""
        SELECT SUM(pri.qty)
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
        WHERE pri.purchase_order = %s AND pri.item_code = %s AND pr.docstatus = 1
    """, (po_name, item_code))[0][0]

    return flt(total_received or 0)

def get_po_item_qty(po_name, item_code):
    if not po_name:
        return 0
    po = frappe.get_doc("Purchase Order", po_name)
    for item in po.items:
        if item.item_code == item_code:
            return item.qty
    return 0

def is_linked_po_fully_billed(self):
    """检查是否有任何关联的 PO 的 per_billed 小于 100"""
    for item in self.items:
        if item.purchase_order:
            print(f"[调试] Item: {item.item_code}, PO: {item.purchase_order}")
            po = frappe.get_doc("Purchase Order", item.purchase_order)
            if flt(po.per_billed) < 100:
                return False
    return True

def get_mr_item_qty(mr_name, item_code):
    if not mr_name:
        return 0
    mr = frappe.get_doc("Material Request", mr_name)
    for item in mr.items:
        if item.item_code == item_code:
            return item.qty
    return 0

def get_pr_item_qty(pr, item_code):
    pr = frappe.get_doc("Purchase Receipt", pr["name"])
    for item in pr.items:
        if item.item_code == item_code:
            frappe.msgprint("pipei")
            return item.qty
        frappe.msgprint("wei pipei")
        return 0
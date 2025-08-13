import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_user_profile_name():
    user = frappe.get_doc("User", frappe.session.user)
    return user.get("role_profile_name")  # 可能返回 None

def mark_inspection_confirmed(docname):
    doc = frappe.get_doc("Purchase Receipt", docname)
    doc.db_set("custom_inspection_confirmed", 1)  # ✅ 强制写入数据库，不依赖 save()

def get_linked_material_request(purchase_receipt_name):
    pr = frappe.get_doc("Purchase Receipt", purchase_receipt_name)

    for item in pr.items:
        if item.material_request:
            return item.material_request

    return None

def get_received_qty(po_name, item_code):
    total_received = frappe.db.sql("""
        SELECT SUM(pri.qty)
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
        WHERE pri.purchase_order = %s AND pri.item_code = %s AND pr.docstatus = 1
    """, (po_name, item_code))[0][0]

    return flt(total_received or 0)

def is_linked_po_fully_billed(self):
    """检查是否有任何关联的 PO 的 per_billed 小于 100"""
    for item in self.items:
        if item.purchase_order:
            print(f"[调试] Item: {item.item_code}, PO: {item.purchase_order}")
            po = frappe.get_doc("Purchase Order", item.purchase_order)
            if flt(po.per_billed) < 100:
                return False
    return True
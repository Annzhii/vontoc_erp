import frappe

@frappe.whitelist()
def convert_to_pi(doc_name):
    frappe.msgprint("1")
    doc = frappe.get_doc("Quotation", doc_name)
    is_temporary_item(doc)
    doc.custom_custom_status = "PI"
    doc.save()

def is_temporary_item(doc):
    for item in doc.items:
        item_group = frappe.db.get_value(
            "Item",
            item.item_code,
            "item_group"
        )

        if item_group == "临时物料":
            frappe.throw(
                f"物料 {item.item_code} 为临时物料，无法创建 PI。请先提交物料创建申请并完成审批流程。"
            )
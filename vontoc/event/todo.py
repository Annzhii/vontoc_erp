import frappe
from frappe.utils import get_url
from pushweb.api.push import send_push_to_user
import re

@frappe.whitelist()
def todo_after_insert(doc, method=None):
    try:
        # 获取 allocated_to 用户
        user = doc.allocated_to
        if not user:
            return  # 如果没有分配用户，跳过

        # 获取 ToDo 描述作为标题
        body = doc.description or "New ToDo"

        # 构造 URL
        if doc.reference_type and doc.reference_name:
            # 根据 reference_type 构造不同的 URL
            route = doc.reference_type.replace(" ", "-").lower()  
            url = get_url(f"/app/{route}/{doc.reference_name}")
        else:
            url = None

        # 发送推送通知
        send_push_to_user(
            to_app="erp",
            user=user,
            title= "You have a new ToDo!",
            body=re.sub(r"<[^>]+>", "", body),  # 任务通知内容
            url=url
        )
    except Exception as e:
        frappe.log_error(
            title=f"todo_after_insert failed for {doc.name}",
            message=str(e)[:140]
        )

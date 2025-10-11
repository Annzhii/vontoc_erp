import frappe
from frappe.utils import get_url
from pushweb.api.push import send_push_to_user
from crm.fcrm.doctype.crm_notification.crm_notification import notify_user
import re

def html_to_text_preserve_newlines(html: str) -> str:
    """将 HTML 转为纯文本，保留换行"""
    if not html:
        return ""
    
    # 替换 <br> 或 <p> 为换行
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p>", "\n", html)
    
    # 去掉其他 HTML 标签
    text = re.sub(r"<[^>]+>", "", html)
    
    # 去掉多余空白行
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join([line for line in lines if line.strip()])

@frappe.whitelist()
def communication_after_insert(doc, method=None):
    if doc.sent_or_received != "Received":
        return

    if doc.reference_doctype not in ("CRM Lead", "CRM Deal"):
        return
    """
    简化版：将 Communication 内容去掉 HTML 后推送给 recipients
    """
    try:
        recipients = doc.recipients or ""
        users = [user.strip() for user in recipients.split(",") if user.strip()]

        body_text = html_to_text_preserve_newlines(doc.content)

        doctype_route_map = {
            "CRM Lead": "leads",
            "CRM Deal": "deals",
        }
        for user in users:
            if doc.reference_doctype and doc.reference_name:
                route = doctype_route_map.get(doc.reference_doctype)
                if route:
                    url = get_url(f"/crm/{route}/{doc.reference_name}#emails")
                    print(url)

            send_push_to_user(
                user=user,
                title=(doc.subject or "New Communication")[:100],
                body=body_text[:400],  # 防止超过 Web Push 限制
                url=url
            )

    except Exception as e:
        frappe.log_error(
            title=f"communication_after_insert failed for {doc.name}",
            message=str(e)[:140]
        )
import frappe
from frappe.utils import get_url
from pushweb.api.push import send_push_to_user
from crm.fcrm.doctype.crm_notification.crm_notification import notify_user
import re
from bs4 import BeautifulSoup

def html_to_text_preserve_newlines(html: str) -> str:
    """HTML 转纯文本、保留换行、自动去除引用旧邮件（blockquotes / Gmail / Outlook）"""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # 删除不需要的标签
    for tag in soup(["style", "script"]):
        tag.decompose()

    # 删除所有 blockquote
    for quote in soup.find_all("blockquote"):
        quote.decompose()

    text = soup.get_text(separator="\n")

    # 删除 Gmail 的 "On xxx wrote:"
    text = re.sub(r"(?im)^On .* wrote:$", "", text)

    # Outlook
    text = re.sub(r"(?im)^(From|Sent|To|Subject): .*", "", text)

    # Apple Mail
    text = re.sub(r"(?im)^-----Original Message-----$", "", text)

    # 去除多余换行
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()

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
                to_app="crm",
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
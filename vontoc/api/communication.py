import frappe
from frappe import _
from bs4 import BeautifulSoup
import re

from crm.fcrm.doctype.crm_notification.crm_notification import notify_user


def after_insert_communication(doc, method):
    if (
        doc.email_account and
        doc.sent_or_received == "Received" and
        doc.reference_doctype in ("CRM Lead", "CRM Deal")
    ):
        notify_communication_creation(doc)

def notify_communication_creation(doc):
    """
    通知分配给用户，告知 Communication 创建的内容
    """
    email_id = frappe.db.get_value("Email Account", doc.email_account, "email_id")
    if email_id:
        email_user = frappe.db.get_value("User", {"email": email_id}, "name")

    assigned_to = email_user or "Administrator"
    owner = frappe.get_cached_value("User", frappe.session.user, "full_name")
    message = _("You received a new mail")

    notification_text = get_notification_text_for_communication(owner, doc)

    redirect_to_doctype, redirect_to_name = get_redirect_to_doc(doc)

    notify_user(
        {
            "owner": frappe.session.user,
            "assigned_to": assigned_to,
            "notification_type": "Task",
            "message": message,
            "notification_text": notification_text,
            "reference_doctype": doc.reference_doctype,
            "reference_docname": doc.reference_name,
            "redirect_to_doctype": redirect_to_doctype,
            "redirect_to_docname": redirect_to_name,
        }
    )


def get_notification_text_for_communication(owner, doc):
    """
    提取 Communication 的首行内容，自动去除引用（兼容 Gmail / Outlook / Apple Mail）。
    """
    html = doc.content or ""
    if not html:
        return _("No content available")

    soup = BeautifulSoup(html, "html.parser")

    # 删除 <style>、<script> 等无用标签
    for tag in soup(["style", "script"]):
        tag.decompose()

    # 删除所有 blockquote（旧邮件）
    for quote in soup.find_all("blockquote"):
        quote.decompose()

    # 获取剩余内容（用户新输入部分）
    text = soup.get_text(separator="\n").strip()

    # 去掉多余空行
    text = re.sub(r"\n{2,}", "\n", text)

    # 获取第一行有效文本
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")

    if len(first_line) > 120:
        first_line = first_line[:120] + "..."

    if not first_line:
        first_line = _("No content available")

    return f"""
        <div class="mb-2 leading-5 text-ink-gray-5">
            <span class="font-medium text-ink-gray-9">{ doc.sender }</span>
            <span>{ _('Sent you a new mail:') }</span>
            <span class="font-medium text-ink-gray-9">{ first_line }</span>
        </div>
    """


def get_redirect_to_doc(doc):
	return doc.reference_doctype, doc.reference_name
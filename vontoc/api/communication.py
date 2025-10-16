import frappe
from frappe import _

from crm.fcrm.doctype.crm_notification.crm_notification import notify_user


def after_insert_communication(doc, method):
    """
    当 Communication 文档插入时，触发通知给相关的用户
    """
    if doc.allocated_to:
        notify_communication_creation(doc)


def notify_communication_creation(doc):
    """
    通知分配给用户，告知 Communication 创建的内容
    """
    owner = frappe.get_cached_value("User", frappe.session.user, "full_name")
    message = _("{0} created a new communication for you").format(owner)

    notification_text = get_notification_text_for_communication(owner, doc)

    redirect_to_doctype, redirect_to_name = get_redirect_to_doc(doc)

    notify_user(
        {
            "owner": frappe.session.user,
            "assigned_to": doc.allocated_to,
            "notification_type": "Task",
            "message": message,
            "notification_text": notification_text,
            "reference_doctype": "CRM Deal",
            "reference_docname": "CRM-DEAL-2025-00009",
            "redirect_to_doctype": "CRM Deal",
            "redirect_to_docname": "CRM-DEAL-2025-00009",
        }
    )


def get_notification_text_for_communication(owner, doc):
    """
    构造 Communication 创建的通知文本
    """
    #communication_content = doc.content or _("No content available")
    return f"""
        <div class="mb-2 leading-5 text-ink-gray-5">
            <span class="font-medium text-ink-gray-9">{ owner }</span>
            <span>{ _('created a new communication:') }</span>
            <span class="font-medium text-ink-gray-9">{ "communication_content" }</span>
        </div>
    """


def get_redirect_to_doc(doc):
    """
    获取跳转到 Communication 文档的链接
    """
    return "Communication", doc.name

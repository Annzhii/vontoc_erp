import frappe
from pushweb.api.push import send_push_to_user

@frappe.whitelist()
def notification_after_insert(doc, method=None):
    try:
        url = frappe.utils.get_url(f"/app/{frappe.scrub(doc.document_type)}/{doc.document_name}")
        
        send_push_to_user(
            to_app="erp",
            user=doc.for_user,
            title=(doc.subject or "New Notification")[:100],
            body=doc.email_content,
            url=url
        )
    except Exception as e:
        frappe.log_error(
            title=f"notification_log_after_insert failed for {doc.name}",
            message=str(e)[:140]
        )
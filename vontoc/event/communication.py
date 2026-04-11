import frappe
from frappe.utils import get_url
from pushweb.api.push import send_push_to_user

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
        print(str(users))

        doctype_route_map = {
            "CRM Lead": "leads",
            "CRM Deal": "deals",
        }
        for user in users:
            if doc.reference_doctype and doc.reference_name:
                route = doctype_route_map.get(doc.reference_doctype)
                if route:
                    url = get_url(f"/crm/{route}/{doc.reference_name}#emails")

            send_push_to_user(
                to_app="crm",
                user=user,
                title=(doc.subject or "New Communication")[:100],
                body="New Email Received",
                url=url
            )

    except Exception as e:
        frappe.log_error(
            title=f"communication_after_insert failed for {doc.name}",
            message=str(e)[:140]
        )
import frappe
from frappe import _

from vontoc_erp.utils.cache import (
	get_default_outgoing_email_for_user,
)

@frappe.whitelist(allow_guest=True)
def get_user_info() -> dict:
	"""Returns user information."""
	print("api 调用成功")
	if frappe.session.user == "Guest":
		return None

	user = frappe.db.get_value(
		"User",
		frappe.session.user,
		[
			"name",
			"email",
			"enabled",
			"user_image",
			"full_name",
			"first_name",
			"last_name",
			"user_type",
			"username",
			"api_key",
		],
		as_dict=1,
	)
	user["roles"] = frappe.get_roles(user.name)
	user.is_mail_user = "Mail User" in user.roles
	user.is_mail_admin = "Mail Admin" in user.roles

	user.default_outgoing = get_default_outgoing_email_for_user(frappe.session.user)

	return user

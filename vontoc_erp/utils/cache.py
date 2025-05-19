import frappe
from frappe import _

def get_default_outgoing_email_for_user(user: str) -> str | None:
	"""Returns the default outgoing email of the user."""

	def generator() -> str | None:
		return frappe.db.get_value("Mail Account", {"user": user, "enabled": 1}, "default_outgoing_email")

	return frappe.cache.hget(f"user|{user}", "default_outgoing_email", generator)

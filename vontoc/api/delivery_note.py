import frappe

def check_allow_shipment(self):
    if self.is_internal_customer == 1:
        return
    if self.is_return == 1:
        return
    if not (self.custom_verified or self.custom_allow_shipment_before_full_payment):
        frappe.throw(
            ("当前发货单未审核，不允许发货。")
        )
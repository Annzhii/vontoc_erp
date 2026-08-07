from frappe import _


def get_data(data=None):
	return {
		"fieldname": "subcontracting_order",
		"non_standard_fieldnames": {"Stock Reservation Entry": "voucher_no", "Purchase Invoice": "custom_subcontracting_order"},
		"transactions": [
			{
				"label": _("Reference"),
				"items": ["Subcontracting Receipt", "Stock Entry", "Purchase Invoice"],
			},
			{
				"label": _("Stock Reservation"),
				"items": ["Stock Reservation Entry"],
			},
		],
	}
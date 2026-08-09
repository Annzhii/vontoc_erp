from frappe import _


def get_data(data=None):
	return {
		"fieldname": "material_request",
		"non_standard_fieldnames": {"Material Request": "custom_material_request"},
		"internal_links": {
			"Sales Order": ["items", "sales_order"],
			"Project": ["items", "project"],
			"Cost Center": ["items", "cost_center"],
			"Material Request": ["items", "custom_material_request"],
		},
		"transactions": [
			{
				"label": _("Reference"),
				"items": ["Sales Order", "Request for Quotation", "Supplier Quotation", "Purchase Order"],
			},
			{"label": _("Stock"), "items": ["Stock Entry", "Purchase Receipt", "Pick List"]},
			{"label": _("Manufacturing"), "items": ["Work Order"]},
			{"label": _("Internal Transfer"), "items": ["Sales Order"]},
			{"label": _("Accounting Dimensions"), "items": ["Project", "Cost Center"]},
			{"label": _("Material Request"), "items": ["Material Request"]}
		],
	}
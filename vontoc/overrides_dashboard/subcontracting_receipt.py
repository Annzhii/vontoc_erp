from frappe import _


def get_data(data=None):
	return {
		"fieldname": "subcontracting_receipt",
		"non_standard_fieldnames": {
			"Subcontracting Receipt": "return_against",
			"Sales Invoice": "custom_subcontracting_receipt",
			"Purchase Invoice": "custom_subcontracting_receipt"
		},
		"internal_links": {
			"Subcontracting Order": ["items", "subcontracting_order"],
			"Purchase Order": ["items", "purchase_order"],
			"Project": ["items", "project"],
			"Quality Inspection": ["items", "quality_inspection"],
		},
		"transactions": [
			{
				"label": _("Reference"),
				"items": [
					"Purchase Order",
					"Purchase Receipt",
					"Subcontracting Order",
					"Quality Inspection",
					"Project",
				],
			},
			{
				"label": _("Subcontracting"),
				"items": [
					"Sales Invoice",
					"Purchase Invoice",
				],
			},
			{"label": _("Returns"), "items": ["Subcontracting Receipt"]},
		],
	}
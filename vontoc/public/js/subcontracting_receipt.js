// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subcontracting Receipt", {
	refresh: (frm) => {

		if (frm.doc.docstatus === 1) {

			frm.add_custom_button(
				__("Purchase Invoice"),
				() => {
					frappe.model.open_mapped_doc({
						method: "vontoc.api.subcontracting_receipt.make_purchase_invoice",
						frm: frm,
						freeze: true,
						freeze_message: __("Creating Purchase Invoice ..."),
					});
				},
				__("Create")
			);


			frm.add_custom_button(
				__("Sales Invoice"),
				() => {
					frappe.model.open_mapped_doc({
						method: "vontoc.api.subcontracting_receipt.make_sales_invoice",
						frm: frm,
						freeze: true,
						freeze_message: __("Creating Sales Invoice ..."),
					});
				},
				__("Create")
			);

		}
	}
});
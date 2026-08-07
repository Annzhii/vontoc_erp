frappe.ui.form.on("Subcontracting Order", {
	setup: (frm) => {
		frm.custom_make_buttons = {
			"Purchase Invoice": "Purchase Invoice",
		};
	},

	refresh: (frm) => {
		frm.add_custom_button(
			__("Purchase Invoice"),
			() => {
				frappe.model.open_mapped_doc({
					method: "vontoc.api.subcontracting_order.make_purchase_invoice",
					frm: frm,
					freeze: true,
					freeze_message: __("Creating Purchase Invoice ..."),
				});
			},
			__("Create")
		);
    }
})
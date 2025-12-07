// Copyright (c) 2025, anzhi and contributors
// For license information, please see license.txt

frappe.ui.form.on('Guideline Price', {
	after_workflow_action: function(frm) {
		if (frm.doc.workflow_state == 'Sent For Quotation') {
			frappe.call({
				method: "vontoc.vontoc.doctype.guideline_price.guideline_price.send_guideline_price",
				args: {
					docname: frm.doc.name,
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint(__(r.message));
					}
				}
			});
		}
		if (frm.doc.workflow_state == 'Draft') {
			frappe.call({
				method: "vontoc.vontoc.doctype.guideline_price.guideline_price.reject_guideline_price",
				args: {
					docname: frm.doc.name,
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint(__(r.message));
					}
				}
			});
		}
	}
});


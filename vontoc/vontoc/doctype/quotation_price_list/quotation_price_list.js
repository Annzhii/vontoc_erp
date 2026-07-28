// Copyright (c) 2025, anzhi and contributors
// For license information, please see license.txt
erpnext.sales_common.setup_selling_controller();
frappe.ui.form.on("Quotation Price List", {
	on_submit: function (frm) {
        frappe.call({
            method: "vontoc.vontoc.doctype.quotation_price_list.quotation_price_list.create_pricing_rules_from_tier",
            args: {
                pricing_tier_name: frm.doc.name
            },
            callback: function(r) {
                frappe.msgprint("定价规则已创建！");
            }
        });        
    },

    refresh(frm) {

        if (!frm.is_new()) {

            frm.add_custom_button(
                __("Request for Quotation"),
                function () {

                    frappe.model.open_mapped_doc({
                        method: "vontoc.vontoc.doctype.quotation_price_list.quotation_price_list.make_rfq",
                        frm: frm
                    });

                },
                __("Create")
            );

        }
    },

	after_workflow_action: function(frm) {
		if (frm.doc.workflow_state == 'Sent For Quotation') {
			frappe.call({
				method: "vontoc.vontoc.doctype.quotation_price_list.quotation_price_list.send_quotation_price_list",
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
		if (frm.doc.workflow_state == 'Quotation Received') {
			frappe.call({
				method: "vontoc.vontoc.doctype.guideline_price.guideline_price.quotation_received",
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

erpnext.selling.QuotationPricingTierController = class QuotationPricingTierController extends erpnext.selling.SellingController {

    tc_name() {
            this.get_terms();
        }
};


cur_frm.script_manager.make(erpnext.selling.QuotationPricingTierController);
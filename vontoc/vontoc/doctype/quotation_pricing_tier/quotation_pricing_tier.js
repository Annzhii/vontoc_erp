// Copyright (c) 2025, anzhi and contributors
// For license information, please see license.txt
erpnext.sales_common.setup_selling_controller();
frappe.ui.form.on("Quotation Pricing Tier", {
	on_submit: function (frm) {
        frappe.call({
            method: "vontoc.vontoc.doctype.quotation_pricing_tier.quotation_pricing_tier.create_pricing_rules_from_tier",
            args: {
                pricing_tier_name: frm.doc.name
            },
            callback: function(r) {
                frappe.msgprint("定价规则已创建！");
            }
        });        
    },
});

erpnext.selling.QuotationPricingTierController = class QuotationPricingTierController extends erpnext.selling.SellingController {

    tc_name() {
            this.get_terms();
        }
};


cur_frm.script_manager.make(erpnext.selling.QuotationPricingTierController);
// Copyright (c) 2025, anzhi and contributors
// For license information, please see license.txt

frappe.ui.form.on('Guideline Price', {
	on_submit: function (frm){
		frappe.call({
			method: "vontoc.vontoc.doctype.guideline_price.guideline_price.rfq_process_step_04",
			args: {
				gp:frm.doc.name
			},
			callback: function(r) {
				if (r.message) {
					frappe.msgprint(__(r.message));
					frm.reload_doc();
				}
			}
		})
	},
    setup(frm) {
        frm.set_query('supplier_quotation', () => {
            if (!frm.doc.rfq) {
                frappe.msgprint(__('Please select RFQ first'));
                return false;
            }

            return {
                filters: {
                    request_for_quotation: frm.doc.rfq
                }
            };
        });
    },

    rfq(frm) {
        // 当 RFQ 改变时，自动清空不相关的 Supplier Quotation
        frm.set_value('supplier_quotation', null);
    },
    
	supplier_quotation: function(frm) {
		if (!frm.doc.supplier_quotation) return;

		frappe.call({
			method: "vontoc.vontoc.doctype.guideline_price.guideline_price.map_supplier_quotation_items",  // 替换为你的实际路径
			args: {
				sq_name: frm.doc.supplier_quotation
			},
			callback: function(r) {
				if (!r.message) return;

				// 清空原有项
				frm.clear_table("items");

				// 添加新项
				r.message.forEach(row => {
					let child = frm.add_child("items", {
						item_code: row.item_code,
						quantity: row.quantity,
						uom: row.uom,
						supplier_price: row.supplier_price
					});
				});

				frm.refresh_field("items");
			}
		});
	}
});


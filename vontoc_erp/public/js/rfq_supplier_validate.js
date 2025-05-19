frappe.ui.form.on('Request for Quotation', {
    before_workflow_action: function(frm) {
        // 目标状态是 Pending 的时候，检查 supplier
        if (frm.doc.workflow_state == 'Pending') {
            let empty_suppliers = frm.doc.suppliers.filter(s => !s.supplier);
            if (empty_suppliers.length > 0) {
                frappe.throw(__('在发送RFQ之前，需要填入供应商。'));
            }
        }
    }
});
frappe.ui.form.on("Material Request", {
    refresh(frm) {
        frm.add_custom_button(
            __("Request for Raw Materials"),
            () => make_raw_material_request(frm),
            __("Create")
        );
    }
});

function make_raw_material_request(frm) {
    frm.call({
        method: "vontoc.api.material_request.get_work_order_items",
        args: {
            material_request: frm.docname
        },
        callback: function (r) {
            if (!r.message) {
                frappe.msgprint({
                    message: __("No Items with Bill of Materials."),
                    indicator: "orange",
                });
                return;
            }

            make_raw_material_request_dialog(frm, r);
        },
    });
}


function make_raw_material_request_dialog(frm, r) {
    var fields = [
        {
            fieldtype: "Check",
            fieldname: "include_exploded_items",
            label: __("Include Exploded Items"),
        },
        {
            fieldtype: "Check",
            fieldname: "ignore_existing_ordered_qty",
            label: __("Ignore Existing Ordered Qty"),
        },
        {
            fieldtype: "Table",
            fieldname: "items",
            description: __("Select BOM, Qty and For Warehouse"),
            fields: [
                {
                    fieldtype: "Read Only",
                    fieldname: "item_code",
                    label: __("Item Code"),
                    in_list_view: 1,
                },
                {
                    fieldtype: "Link",
                    fieldname: "warehouse",
                    options: "Warehouse",
                    label: __("For Warehouse"),
                    in_list_view: 1,
                },
                {
                    fieldtype: "Link",
                    fieldname: "bom",
                    options: "BOM",
                    reqd: 1,
                    label: __("BOM"),
                    in_list_view: 1,
                    get_query: function (doc) {
                        return {
                            filters: {
                                item: doc.item_code,
                            },
                        };
                    },
                },
                {
                    fieldtype: "Float",
                    fieldname: "required_qty",
                    reqd: 1,
                    label: __("Qty"),
                    in_list_view: 1,
                },
            ],
            data: r.message,
            get_data: function () {
                return r.message;
            },
        },
    ];


    let d = new frappe.ui.Dialog({
        title: __("Items for Raw Material Request"),
        fields: fields,

        primary_action() {
            let data = d.get_values();

            frm.call({
                method: "vontoc.api.material_request.make_raw_material_request",
                args: {
                    items: data,
                    company: frm.doc.company,
                    material_request: frm.docname,
                    project: frm.doc.project,
                },
                freeze: true,

                callback(r) {
                    if (r.message) {
                        frappe.msgprint(
                            __("Material Request {0} submitted.", [
                                `<a href="/app/material-request/${r.message.name}">
                                    ${r.message.name}
                                </a>`,
                            ])
                        );
                    }

                    d.hide();
                    frm.reload_doc();
                },
            });
        },

        primary_action_label: __("Create"),
    });

    d.show();
}
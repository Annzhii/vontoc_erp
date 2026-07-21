// item的quick entry自定义
frappe.provide("frappe.ui.form");

frappe.ui.form.ItemQuickEntryForm = class ItemQuickEntryForm extends frappe.ui.form.QuickEntryForm {

	set_meta_and_mandatory_fields() {
		this.meta = frappe.get_meta(this.doctype);
		let fields = this.meta.fields;

		this.docfields = fields.filter((df) => {
			return (
				(df.reqd || df.allow_in_quick_entry) &&
				!df.is_virtual &&
				df.fieldtype !== "Tab Break"
			);
		});

        this.docfields.push({
            fieldname: "_image",
            fieldtype: "Attach Image",
            label: "Image"
        });
	}

    update_doc() {
        super.update_doc();
        this.doc.image = this.get_value("_image");
    }
	render_dialog() {
		super.render_dialog();

		const field_rules = {
			custom_sizemm: [
				"注塑制件",
				"镶件",
				"注塑成型",
				"注塑模具",
				"纸箱"
			],

			custom_cavity_number: [
				"注塑模具"
			]
		};


		Object.entries(field_rules).forEach(([fieldname, allowed_groups]) => {
			const field = this.fields_dict[fieldname];

			if (field) {
				const original_get_status = field.get_status.bind(field);
				field.get_status = function () {
					const group = this.doc.custom_requested_item_group;

					if (allowed_groups.includes(group)) {
						return "Read";
					}

					return original_get_status();
				};

				field.refresh();
			}
		});
		const update_size = () => {
			const d = this.fields_dict.custom_diametermm.get_value();
			const l = this.fields_dict.custom_lengthmm.get_value();
			const w = this.fields_dict.custom_widthmm.get_value();
			const h = this.fields_dict.custom_highmm.get_value();

			let size = "";

			if (d && h) {
				size = `${d}X${h}`;
			} else if (l && w && h) {
				size = `${l}X${w}X${h}`;
			}

			this.fields_dict.custom_sizemm.set_value(size);
		};

		["custom_lengthmm", "custom_widthmm", "custom_highmm", "custom_diametermm"].forEach(f => {
			const field = this.fields_dict[f];

			if (field && field.$input) {
				field.$input.on("change", update_size);
			}
		});
	}
}
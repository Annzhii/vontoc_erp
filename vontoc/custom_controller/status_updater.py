import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form

def _update_prevdoc_status(self):
	self.update_qty()
	validate_qty(self)

def validate_qty(self):
    """Validates qty at row level"""
    self.item_allowance = {}
    self.global_qty_allowance = None
    self.global_amount_allowance = None

    for args in self.status_updater:
        if "target_ref_field" not in args:
            # if target_ref_field is not specified, the programmer does not want to validate qty / amount
            continue

        items_to_validate = []

        # get unique transactions to update
        for d in self.get_all_children():
            if hasattr(d, "qty") and d.qty < 0 and not self.get("is_return"):
                frappe.throw(_("For an item {0}, quantity must be positive number").format(d.item_code))

            if hasattr(d, "qty") and d.qty > 0 and self.get("is_return"):
                frappe.throw(_("For an item {0}, quantity must be negative number").format(d.item_code))

            if not frappe.get_single_value("Selling Settings", "allow_negative_rates_for_items"):
                if hasattr(d, "item_code") and hasattr(d, "rate") and flt(d.rate) < 0:
                    frappe.throw(
                        _(
                            "For item {0}, rate must be a positive number. To Allow negative rates, enable {1} in {2}"
                        ).format(
                            frappe.bold(d.item_code),
                            frappe.bold(_("`Allow Negative rates for Items`")),
                            get_link_to_form("Selling Settings", "Selling Settings"),
                        ),
                    )

            if d.doctype == args["source_dt"] and d.get(args["join_field"]):
                items_to_validate.append(
                    frappe._dict(
                        {
                            "name": d.get(args["join_field"]),
                            "production_plan_sub_assembly_item": d.get(
                                "production_plan_sub_assembly_item"
                            ),
                            "idx": d.idx,
                            "child_doc": d,
                        }
                    )
                )

        if items_to_validate:
            pp_sub_assembly_items = [
                item.production_plan_sub_assembly_item
                for item in items_to_validate
                if item.production_plan_sub_assembly_item
            ]

            pp_subcontract_items = []
            if pp_sub_assembly_items:
                pp_subcontract_items = frappe.db.get_all(
                    "Production Plan Sub Assembly Item",
                    filters={
                        "name": ("in", pp_sub_assembly_items),
                        "type_of_manufacturing": "Subcontract",
                    },
                    pluck="name",
                )

            regular_items = []
            pp_items = []

            for item in items_to_validate:
                if item.production_plan_sub_assembly_item in pp_subcontract_items:
                    pp_items.append(item.name)
                else:
                    regular_items.append(item.name)

            item_details = []

            # Query regular items with item_code field
            if regular_items:
                item_details.extend(self.fetch_items_with_pending_qty(args, "rm_item_code", regular_items))

            # Query production plan items with production_item field
            if pp_items:
                item_details.extend(self.fetch_items_with_pending_qty(args, "production_item", pp_items))

            item_lookup = {item.name: item for item in item_details}

            for child_item in items_to_validate:
                item = item_lookup.get(child_item.name)

                if item:
                    item["idx"] = child_item.idx
                    item["target_ref_field"] = args["target_ref_field"].replace("_", " ")

                    # if not item[args['target_ref_field']]:
                    # 	msgprint(_("Note: System will not check over-delivery and over-booking for Item {0} as quantity or amount is 0").format(item.item_code))
                    if args.get("no_allowance"):
                        item["reduce_by"] = item[args["target_field"]] - item[args["target_ref_field"]]
                        if item["reduce_by"] > 0.01:
                            self.limits_crossed_error(args, item, "qty")

                    elif item[args["target_ref_field"]]:
                        self.check_overflow_with_allowance(item, args)
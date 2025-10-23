# Copyright (c) 2025, anzhi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.controllers.selling_controller import SellingController

class QuotationPriceList(SellingController):
    def calculate_taxes_and_totals(self):
        pass
    def abs(self):
        pass
    def validate(self):
        pass
     
from frappe.utils import nowdate

@frappe.whitelist()
def create_pricing_rules_from_tier(pricing_tier_name):
    pricing_tier = frappe.get_doc("Quotation Price List", pricing_tier_name)

    # 按 item_code 分组
    from collections import defaultdict
    grouped_items = defaultdict(list)

    for row in pricing_tier.items:
        if row.item_code and row.qty and row.rate:
            grouped_items[row.item_code].append({
                "quantity": row.qty,
                "rate": row.rate
            })

    for item_code, rules in grouped_items.items():
        # 按 quantity 升序排序
        rules = sorted(rules, key=lambda x: x["quantity"])

        for i, rule in enumerate(rules):
            min_qty = rule["quantity"]
            rate = rule["rate"]

            # 设置 max_qty：当前不是最后一个，则是下一个的 quantity - 1；否则为 None
            if i < len(rules) - 1:
                max_qty = rules[i+1]["quantity"] - 1
            else:
                max_qty = None

            pricing_rule = frappe.new_doc("Pricing Rule")
            pricing_rule.naming_series = "PRULE-.YYYY.-"
            pricing_rule.title = f"{item_code} Tier {min_qty}+"
            pricing_rule.item_code = item_code
            pricing_rule.selling = 1
            pricing_rule.rate_or_discount = "Rate"
            pricing_rule.rate = rate
            pricing_rule.min_qty = min_qty
            if max_qty:
                pricing_rule.max_qty = max_qty

            # 设置定价规则生效的项目列表
            pricing_rule.append("items", {
                "item_code": item_code
            })

            # 可选：设置有效期
            pricing_rule.valid_from = nowdate()
            pricing_rule.save()
            frappe.msgprint(f"Pricing Rule for {item_code}, Qty ≥ {min_qty} created.")

    return "Pricing Rules Created"


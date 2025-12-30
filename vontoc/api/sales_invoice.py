import frappe

def sync_sales_invoice_to_delivery_note(self):
    """
    同步 SI.payment_dn <-> DN.sales_invoice_reference
    规则：
    - SI 子表新增 → DN 子表新增
    - SI 子表删除 → DN 子表删除
    - SI 子表修改 allocated_amount → DN 子表同步修改
    """

    # 构造 SI 侧的映射：{(delivery_note): allocated_amount}
    si_map = {}
    for row in self.custom_details:
        if not row.delivery_note:
            continue
        si_map[row.delivery_note] = row.allocated_amount or 0
    # 找出所有相关 DN
    dn_names = list(si_map.keys())

    for dn_name in dn_names:
        dn = frappe.get_doc("Delivery Note", dn_name)

        # 是否已经存在指向该 SI 的行
        matched_row = None
        for row in dn.custom_details:
            if row.sales_invoice == self.name:
                matched_row = row
                break

        # 新增或更新
        if matched_row:
            if dn.docstatus == 1:
                frappe.throw(
                    f"Delivery Note {dn.name} 已提交，不能修改关联的 Sales Invoice {self.name}"
                )
            if dn.custom_verified == 1:
                frappe.throw(
                    f"Delivery Note {dn.name} 已被审核，不能修改关联的 Sales Invoice {self.name}"
                )
            if matched_row.allocated_amount != si_map[dn_name]:
                matched_row.allocated_amount = si_map[dn_name]
        else:
            dn.append("custom_details", {
                "sales_invoice": self.name,
                "allocated_amount": si_map[dn_name]
            })
        update_dn_total_allocated(dn)
        dn.save(ignore_permissions=True)

    # 处理「SI 中已删除，但 DN 中仍存在」的情况
    # 找出所有 DN 中引用了该 SI，但 SI.payment_dn 中已经没有的
    orphan_rows = frappe.db.sql("""
        SELECT
            dn.name AS dn_name,
            sir.name AS sir_name
        FROM `tabDelivery Note` dn
        JOIN `tabDelivery Note SI` sir
            ON sir.parent = dn.name
        WHERE sir.sales_invoice = %s
    """, self.name, as_dict=True)

    for row in orphan_rows:
        if row.dn_name not in si_map:
            dn = frappe.get_doc("Delivery Note", row.dn_name)
            if dn.docstatus == 1:
                frappe.throw(
                    f"Delivery Note {dn.name} 已提交，不能移除关联的 Sales Invoice {self.name}"
                )
            if dn.custom_verified == 1:
                frappe.throw(
                    f"Delivery Note {dn.name} 已被审核，不能移除关联的 Sales Invoice {self.name}"
                )
            dn.custom_details = [
                r for r in dn.custom_details
                if r.sales_invoice != self.name
            ]
            update_dn_total_allocated(dn)
            dn.save(ignore_permissions=True)

def update_dn_total_allocated(dn):
    dn.custom_total_allocated_amount = sum(
        (r.allocated_amount or 0) for r in dn.custom_details
    )
    if dn.custom_total_allocated_amount == dn.total:
        dn.custom_payment_status = "Full Allocated"
    elif dn.custom_total_allocated_amount < dn.total:
        dn.custom_payment_status = "Partial Allocated"
    elif dn.custom_total_allocated_amount == 0:
        dn.custom_payment_status = "No Allocated"
    else:
        frappe.throw(
            f"总核销金额 {dn.custom_total_allocated_amount} 超过了发货金额，请检查。"
        )

def check_allocated_amount(self):
    total_allocated = self.custom_total_allocated_amount or 0
    total_amount = self.total or 0

    if total_allocated > total_amount:
        frappe.throw(
            f"核销金额 {total_allocated} 不能大于发票总金额 {total_amount}"
        )
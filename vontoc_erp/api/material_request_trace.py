import frappe

@frappe.whitelist()
def material_request_trace(docname):
    """根据 Material Request 编号，追踪流程链"""
    material_request = frappe.get_doc("Material Request", docname)

    root = {
        "type": "Material Request",
        "name": material_request.name,
        "workflow_state": material_request.workflow_state or "",
        "history": get_workflow_history("Material Request", material_request.name),
        "children": [],
        "so": []
    }

    for item in material_request.items:
        #1 找到对应的sales_order表单
        if item.sales_order and not any(so['name'] == item.sales_order for so in root['so']):
            so_doc = frappe.get_doc("Sales Order", item.sales_order)
            so_node = {
                "type": "Sales Order",
                "name": so_doc.name,
                "workflow_state": getattr(so_doc, 'workflow_state', so_doc.status) or "",
                "history": get_workflow_history("Sales Order", so_doc.name),
                "children": []
            }
            # 找到 Sales Invoice
            sales_invoices = frappe.get_all("Sales Invoice",
                filters={"sales_order": so_doc.name},
                fields=["name", "status"]
            )

            for si in sales_invoices:
                si_doc = frappe.get_doc("Sales Invoice", si.name)
                si_node = {
                    "type": "Sales Invoice",
                    "name": si.name,
                    "workflow_state": getattr(si_doc, 'workflow_state', si_doc.status) or "",
                    "history": get_workflow_history("Sales Invoice", si.name),
                    "children": []
                }

                # 找到 Payment Entry（通过 references 关系）
                payment_entries = frappe.get_all("Payment Entry Reference",
                    filters={
                        "reference_doctype": "Sales Invoice",
                        "reference_name": si.name
                    },
                    fields=["parent as name"],
                    distinct=True
                )

                for pe in payment_entries:
                    pe_doc = frappe.get_doc("Payment Entry", pe.name)
                    pe_node = {
                        "type": "Payment Entry",
                        "name": pe_doc.name,
                        "workflow_state": getattr(pe_doc, 'workflow_state', pe_doc.status) or "",
                        "history": get_workflow_history("Payment Entry", pe_doc.name),
                        "children": []
                    }
                    si_node['children'].append(pe_node)

                so_node['children'].append(si_node)

            root['so'].append(so_node)

    # 2 找到关联的 Purchase Order
    po_list = frappe.get_all("Purchase Order",
        filters={"material_request": material_request.name},
        fields=["name", "status"]
    )

    for po in po_list:
        po_node = {
            "type": "Purchase Order",
            "name": po.name,
            "workflow_state": po.status or "",
            "history": get_workflow_history("Purchase Order", po.name),
            "children": []
        }

        # 找 Purchase Order 对应的 Payment Request
        payment_requests = frappe.get_all("Payment Request",
            filters={
                "reference_doctype": "Purchase Order",
                "reference_name": po.name
            },
            fields=["name", "status"]
        )

        for pr in payment_requests:
            workflow_or_status = pr.workflow_state or pr.status or ""
            pr_node = {
                "type": "Payment Request",
                "name": pr.name,
                "workflow_state": workflow_or_status,
                "history": get_workflow_history("Payment Request", pr.name),
                "children": []
            }

            # 通过子表 Payment Entry Reference 找 Payment Entry
            payment_entries = frappe.db.get_all("Payment Entry Reference",
                filters={
                    "payment_request": pr.name
                },
                fields=["parent as name"],  # parent 字段就是主单 Payment Entry 的 name
                distinct=True
            )

            for pe in payment_entries:
                workflow_or_status_pe = pe.workflow_state or pe.status or ""
                pe_doc = frappe.get_doc("Payment Entry", pe.name)
                pe_node = {
                    "type": "Payment Entry",
                    "name": pe_doc.name,
                    "workflow_state": workflow_or_status_pe,
                    "history": get_workflow_history("Payment Entry", pe_doc.name),
                    "children": []
                }
                pr_node["children"].append(pe_node)

            po_node["children"].append(pr_node)

        root["children"].append(po_node)

    return root


def get_workflow_history(doctype, docname):
    doc_created = frappe.db.get_value(doctype, docname, ["creation", "owner"], as_dict=1)
    """取单据的状态变更历史"""
    version = frappe.db.get_all('Version',
        filters={
            "ref_doctype": doctype,
            "docname": docname,
            "data": ["like", "%workflow_state%"]
        },
        fields=["creation", "data"],
        order_by="creation asc"
    )

    timeline = [{
        "workflow_state": "Draft",
        "timestamp": doc_created.creation
    }]
    for v in version:
        try:
            changes = frappe.parse_json(v.data).get('changed', [])
            for change in changes:
                if change[0] == 'workflow_state':
                    timeline.append({
                        "workflow_state": change[2],  # 改成后的状态
                        "timestamp": v.creation
                    })
        except Exception:
            pass

    return timeline

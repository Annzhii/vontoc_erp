import frappe
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.utils import is_source_fully_generated, get_suppliers_warehouse_name, if_full_received
from frappe.workflow.doctype.workflow_action.workflow_action import apply_workflow

@frappe.whitelist()
def send_subcontracting_receipt(docname):
    sub_pr = frappe.get_doc("Subcontracting Receipt", docname)
    sub_pos = set()
    for item in sub_pr.items:
        sub_pos.add(item.subcontracting_order)

    to_close = [
        {
            "doctype": "Subcontracting Order",
            "docname": sub_po,
        }
        for sub_po in sub_pos if is_source_fully_generated(
            {
                "source_doc": {"doctype": "Subcontracting Order", "docname": sub_po},
                "generated_doc": {"doctype": "Subcontracting Receipt", "field": "subcontracting_order"}
            })
    ]

    suppliers_group_warehouse = get_suppliers_warehouse_name(sub_pr.company)
    supplier_warehouse = frappe.get_doc("Warehouse", sub_pr.set_warehouse)
    
    if supplier_warehouse.parent_warehouse == suppliers_group_warehouse:
        user = "Robot"
        auto_stock = True
    else:
        user = "Stock Manager"
        auto_stock = False

    to_open = [{
        "doctype": "Subcontracting Receipt",
        "docname": sub_pr.name,
        "user": user,
        "description": "收到货物后，核对到货数量与收货单（Subcontracting Receipt）中记录的数量是否一致。确认无误后，完成入库操作，并更新库存记录。",
    }]

    pf_name = get_process_flow_trace_id_by_reference("Subcontracting Order", sub_pos)

    process_flow_trace_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Subcontracting Receipt",
        "ref_docname": sub_pr.name,
        "todo_name": None
    }

    if not pf_name:
        return
    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info=process_flow_trace_info)
    if auto_stock:
        apply_workflow(sub_pr, "Stock")

def stock_subcontracting_receipt(docname):
    
    sub_pr = frappe.get_doc("Subcontracting Receipt", docname)

    to_close = [{
        "doctype": "Subcontracting Receipt",
        "docname": docname
    }]

    sub_pos = set()
    for item in sub_pr.items:
        sub_pos.add(item.subcontracting_order)

    pos = set()
    for sub_po in sub_pos:
        sub_po = frappe.get_doc("Subcontracting Order", sub_po)
        po = sub_po.purchase_order
        pos.add(po)
    
    mrs = set()
    for po in pos:
        po = frappe.get_doc("Purchase Order", po)
        for item in po.items:
            mrs.add(item.material_request)
    for mr in mrs:
        full_received = if_full_received(mr)
        if full_received == False:
            trace = ""
        else:
            trace = "close"

        pf_name = get_process_flow_trace_id_by_reference("Material Request", [mr])

        process_flow_trace_info = {
            "trace": trace,
            "pf_name": pf_name,
            "todo_name": None
        }
        if not pf_name:
            return
        process_flow_engine(to_close=to_close, process_flow_trace_info=process_flow_trace_info)
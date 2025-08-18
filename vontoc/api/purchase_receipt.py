import frappe
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.utils import mark_inspection_confirmed, get_linked_material_request
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice


@frappe.whitelist()
def item_quality_inspection_or_not(docname, has_inspection_required):

    if isinstance(has_inspection_required, str):
        has_inspection_required = has_inspection_required.lower() == 'true'

    assigned_user = "inspection" if has_inspection_required else "stock"
    description = "完成质检" if has_inspection_required else "确认入库"

    to_close = [{
        "doctype": "Purchase Receipt",
        'docname': docname
    }]

    to_open = [{
        "doctype": "Purchase Receipt",
        "docname": docname,
        "user": assigned_user,
        "description": description,
    }]

    _reference = get_linked_material_request(docname)
    pf_name = get_process_flow_trace_id_by_reference("Material Request", _reference)

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Purchase Receipt",
        "ref_docname": docname,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

@frappe.whitelist()
def quality_inspection_finished(docname):
    mark_inspection_confirmed(docname)
    assigned_user = "stock"
    description = "确认入库"

    to_close = [{
        "doctype": "Purchase Receipt",
        "docname": docname
    }]

    to_open = [{
        "doctype": "Purchase Receipt",
        "docname": docname,
        "user": assigned_user,
        "description": description
    }]

    # 获取所有关联的 Quality Inspection 名字（去重）
    def get_linked_quality_inspections(pr_name):
        pr = frappe.get_doc("Purchase Receipt", pr_name)
        qi_names = set()

        for item in pr.items:
            if item.quality_inspection:
                qi_names.add(item.quality_inspection)

        return list(qi_names)

    qi_names = get_linked_quality_inspections(docname)

    if not qi_names:
        frappe.throw("找不到关联的 Quality Inspection")

    _reference = get_linked_material_request(docname)
    pf_name = get_process_flow_trace_id_by_reference("Material Request", _reference)

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Quality Inspection",
        "ref_docname": qi_names[0],
        "todo_name": None
    }

    process_flow_engine(
        to_close=to_close,
        to_open=to_open,
        process_flow_trace_info=process_flow_info
    )

def create_new_pr_for_shortfall(original_doc, shortfall_items):
    pr = frappe.new_doc("Purchase Receipt")
    pr.supplier = original_doc.supplier
    pr.set_posting_time = 1
    pr.posting_date = frappe.utils.nowdate()
    pr.set_warehouse = original_doc.set_warehouse

    for item in shortfall_items:
        pr.append("items", {
            "item_code": item["item_code"],
            "qty": item["qty"],
            "purchase_order": item["po"],
            "material_request":item["rfq"],
            "schedule_date": frappe.utils.nowdate(),
            "warehouse": original_doc.set_warehouse
        })

    pr.insert()

    to_close = [{
        "doctype": "Purchase Receipt",
        "docname": original_doc.name
    }]

    to_open = [{
        "doctype": "Purchase Receipt",
        "docname": pr.name,
        "user": "purchase",
        "description": "提交收货单"
    }]

    _reference = get_linked_material_request(original_doc.name)
    pf_name = get_process_flow_trace_id_by_reference("Material Request", _reference)

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Purchase Receipt",
        "ref_docname": pr.name,
        "todo_name": None
    }
    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

def create_purchase_invoice_from_pr(self):
    linked_pos = list({item.purchase_order for item in self.items if item.purchase_order})
    for po in linked_pos:
        inv = make_purchase_invoice(po)
        inv.insert()

    to_close = [{
        "doctype": "Purchase Receipt",
        "docname": self.name
    }]

    to_open = [{
        "doctype": "Purchase Invoice",
        "docname": inv.name,
        "user": "purchase",
        "description": "审核采购发票上面的金额,并让供应商开具相应金额发票"
    }]

    _reference = get_linked_material_request(self.name)
    pf_name = get_process_flow_trace_id_by_reference("Material Request", _reference)
    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Purchase Invoice",
        "ref_docname": inv.name,
        "todo_name": None
    }
    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

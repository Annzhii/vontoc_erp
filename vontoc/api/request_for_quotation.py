import frappe
from vontoc.utils.todo import set_todo, close_todo
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.process_engine import process_flow_engine
from frappe import _

@frappe.whitelist()
def rfq_process_step_03(rfq):

    to_close =[{
        "doctype":"Request for Quotation",
        "docname":rfq
    }]
    #启动下一步骤
    _rfq = frappe.get_doc("Request for Quotation", rfq)

    if _rfq.get("custom_purpose") != "Sales Pricing":
        frappe.db.set_value("Request for Quotation", rfq, "custom_show_custom_button", 0)
        return "success"

    gp = frappe.new_doc("Guideline Price")
    gp.rfq = _rfq.name

    for item in _rfq.items:
        gp.append("items", {
            "item_code": item.item_code,
            "quantity": item.qty,
            "uom": item.uom,
        })

    gp.insert(ignore_permissions=True)
    frappe.db.set_value("Request for Quotation", rfq, "custom_show_custom_button", 0)

    to_open = [{
        "doctype": "Guideline Price",
        "docname": gp.name,
        "user": "Product Pricelist",
        "description": "请报指导价格",
    }]

    doctype = "Request for Quotation"
    docname = rfq
    trace_name = get_process_flow_trace_id_by_reference(doctype,docname)

    process_flow_trace_info = {
        "trace": "add",
        "pf_name": trace_name,
        "ref_doctype": "Guideline Price",
        "ref_docname": gp.name,
        "todo_name": None
    }
    process_flow_engine(to_open = to_open, to_close = to_close, process_flow_trace_info=process_flow_trace_info)

@frappe.whitelist()
def rfq_process_step_01(rfq):
    process_flow_trace_info={
        "trace": "setup",
        "pf_type": "RFQ",
        "ref_doctype": "Request for Quotation",
        "ref_docname": rfq
    }
    pf_name = process_flow_engine(process_flow_trace_info=process_flow_trace_info)

    to_open= [{
        "doctype": "Request for Quotation",
        "docname": rfq,
        "user": "Purchase",
        "description": "请向供应商发送询价",
    }]

    _process_flow_trace_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Request for Quotation",
        "ref_docname": rfq,
        "todo_name": None
    }
    process_flow_engine(to_open = to_open, process_flow_trace_info=_process_flow_trace_info)

@frappe.whitelist()
def rfq_process_step_02(rfq):

    to_close = [{
        "doctype":"Request for Quotation",
        "docname":rfq
    }]

    to_open = [{
        "doctype":"Request for Quotation",
        "docname":rfq,
        "user": "Purchase",
        "description": "请在所有供应商报价后提交报价"
    }]
    
    doctype = "Request for Quotation"
    docname = rfq
    pf_name = get_process_flow_trace_id_by_reference(doctype, docname)

    _process_flow_trace_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Request for Quotation",
        "ref_docname": rfq,
        "todo_name": None
    }

    process_flow_engine(to_open = to_open, to_close = to_close, process_flow_trace_info=_process_flow_trace_info)

@frappe.whitelist()
def has_zero_rate_items(rfq):
    doc = frappe.get_doc("Request for Quotation", rfq)
    for item in doc.items:
        if not item.rate or float(item.rate) == 0:
            return {"has_zero": True}
    return {"has_zero": False}

def check_supplier(self):
    empty_suppliers = [s for s in self.suppliers if not s.supplier]
    if empty_suppliers:
        frappe.throw(_("在发送RFQ之前，需要填入供应商。"))

@frappe.whitelist()
def check_supplier_quotation_exists(supplier, rfq):
    # 查找该供应商的所有供应商报价单
    existing_quotation = frappe.get_all('Supplier Quotation', filters={'supplier': supplier}, fields=['name'])

    rfq_exists = False
    # 遍历每个供应商报价单
    for sq in existing_quotation:
        # 查找该供应商报价单中的所有子表条目
        items = frappe.get_all('Supplier Quotation Item', filters={'parent': sq.name}, fields=['request_for_quotation'])
        
        # 检查子表中的条目是否匹配目标的 RFQ
        for item in items:
            if item.request_for_quotation == rfq:
                rfq_exists = True
                break
        
        # 如果已经找到匹配的 RFQ，终止遍历
        if rfq_exists:
            break

    return {'exists': rfq_exists}
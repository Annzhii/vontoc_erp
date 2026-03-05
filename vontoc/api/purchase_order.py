import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import make_subcontracting_order
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference 
from vontoc.utils.utils import is_source_fully_generated
from frappe import _
from vontoc.api.overrides_whitelist import make_inter_company_transaction

@frappe.whitelist()
def sent_po_for_approval(docname):
    po = frappe.get_doc("Purchase Order", docname)
    mrs = set()
    for item in po.items:
        mrs.add(item.material_request)
        
    to_close = [
        {
            "doctype": "Material Request",
            "docname": mr,
        }
        for mr in mrs if is_source_fully_generated(
            {
                "source_doc": {"doctype": "Material Request", "docname": mr},
                "generated_doc": {"doctype": "Purchase Order", "field": "material_request"}
            })
    ]
    # 驳回后再提交po，关闭任务
    to_close.append({
            "doctype": "Purchase Order",
            "docname": docname
        })

    to_open = [{
        "doctype": "Purchase Order",
        "docname": po.name,
        "user": "Purchase Master Manager",
        "description": "审核并审批采购订单（Purchase Order），确认物料、数量、价格及供应商信息是否符合公司采购政策和预算要求。",
    }]
    
    pf_name = get_process_flow_trace_id_by_reference("Material Request", mrs)

    process_flow_trace_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Purchase Order",
        "ref_docname": po.name,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_trace_info)

@frappe.whitelist()
def reject_po(docname):
    po = frappe.get_doc("Purchase Order", docname)
    to_close = [
        {
            "doctype": "Purchase Order",
            "docname": docname
        }
    ]
    to_open = [{
        "doctype": "Purchase Order",
        "docname": po.name,
        "user": "Purchase Manager",
        "description": "根据采购主管的驳回意见，修改采购申请（Purchase Order），完善物料、数量、价格或供应商等信息，确保符合审批要求。",
    }]
    pf_name = get_process_flow_trace_id_by_reference("Purchase Order", [docname])

    process_flow_trace_info = {
        "trace": "add",
        "pf_name": pf_name,
        #"ref_doctype": "Purchase Order",
        #"ref_docname": po.name,
        "todo_name": None
    }
    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_trace_info)

def approve_po(self):

    if not self.is_subcontracted:
        approve_purchase_order(self)
    else:
        approve_subcontracted_order(self)

def approve_purchase_order(self):

    if self.is_internal_supplier == 1:
        SO = make_inter_company_transaction("Purchase Order", self.name)
        finished_warehouse = frappe.db.get_value(
            "Company",
            SO.company,
            "default_fg_warehouse"
        )
        if not finished_warehouse:
            frappe.throw(_("Default finished goods warehouse does not exist. Please create it first."))
        contact_person = frappe.db.get_value(
            "Customer",
            SO.customer,
            "customer_primary_contact"
        )
        if not contact_person:
            frappe.throw(_("Customer Primary Contact does not exist. Please create it first."))
        SO.contact_person = contact_person
        SO.delivery_date = self.schedule_date
        SO.set_warehouse = finished_warehouse
        SO.insert(ignore_permissions=True)
        SO.submit()
        return
    
    to_close = [
        {
            "doctype": "Purchae Order",
            "docname": self.name
        }
    ]

    to_open = [{
        "doctype": "Purchase Order",
        "docname": self.name,
        "user": "Purchase Manager",
        "description": "跟进供应商的货物交期，确认发货数量后，在系统中提交采购收货单（Purchase Receipt））。",
    }]

    pf_name = get_process_flow_trace_id_by_reference("Purchase Order", [self.name])

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)

def approve_subcontracted_order(self):

    sub_po = make_subcontracting_order(self.name, notify=True)
    company_abbr = frappe.get_value("Company", self.company, "abbr")
    supplier_warehouse = f"{self.supplier} - {company_abbr}"
    if not supplier_warehouse:
        frappe.throw(_("Supplier Warehouse does not exist. Please create it first."))
    sub_po.supplier_warehouse = supplier_warehouse
    sub_po.submit()
    to_close = [
        {
            "doctype": "Purchase Order",
            "docname": self.name
        }
    ]

    to_open = [{
        "doctype": "Subcontracting Order",
        "docname": sub_po.name,
        "user": "Purchase Manager",
        "description": "按需为分包采购合同调度原料。跟进供应商的货物交期，确认发货数量后，在系统中提交采购收货单（Purchase Receipt））。",
    },
    {
        "doctype": "Purchase Order",
        "docname": self.name,
        "user": "Purchase Manager",
        "description": "跟进并核实分包服务（外加工）的执行进度，服务完成后，及时提交对应的收货单以完成流程记录。",
    }]

    pf_name = get_process_flow_trace_id_by_reference("Purchase Order", [self.name])

    process_flow_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Subcontracting Order",
        "ref_docname": sub_po.name,
        "todo_name": None
    }

    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_info)
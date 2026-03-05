import frappe
from vontoc.utils.process_engine import process_flow_engine
from vontoc.utils.processflow import get_process_flow_trace_id_by_reference
from vontoc.utils.utils import is_source_fully_generated, get_suppliers_warehouse_name, if_full_received
from frappe.workflow.doctype.workflow_action.workflow_action import apply_workflow
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

@frappe.whitelist()
def confirm_purchase_receipt(docname):

    pr = frappe.get_doc("Purchase Receipt", docname)
    
    pos = set()
    item_types = set()
    for item in pr.items:
        pos.add(item.purchase_order)
        item_doc = frappe.get_doc("Item", item.item_code)
        item_types.add(item_doc.is_stock_item)

    if len(item_types) > 1:
        frappe.msgprint(
            "这张收货单包含<b>追踪库存</b>和<b>不追踪库存</b>的物料。<br>"
            "请将这两种类型的物料分开到不同的收货单中处理。",
            title="物料类型混合",
            indicator="red"
        )

    to_close = [
        {
            "doctype": "Purchase Order",
            "docname": po,
        }
        for po in pos if is_source_fully_generated(
            {
                "source_doc": {"doctype": "Purchase Order", "docname": po},
                "generated_doc": {"doctype": "Purchase Receipt", "field": "purchase_order"}
            })
    ]

    suppliers_group_warehouse = get_suppliers_warehouse_name(pr.company)
    supplier_warehouse = frappe.get_doc("Warehouse", pr.set_warehouse)

    if (0 in item_types or supplier_warehouse.parent_warehouse == suppliers_group_warehouse):
        user = "Robot"
        auto_stock = True
    else:
        user = "Stock Manager"
        auto_stock = False

    to_open = [{
        "doctype": "Purchase Receipt",
        "docname": pr.name,
        "user": user,
        "description": "收到货物后，核对到货数量与收货单（Purchase Receipt）中记录的数量是否一致。确认无误后，完成入库操作，并更新库存记录。",
    }]
    
    pf_name = get_process_flow_trace_id_by_reference("Purchase Order", pos)

    process_flow_trace_info = {
        "trace": "add",
        "pf_name": pf_name,
        "ref_doctype": "Purchase Receipt",
        "ref_docname": pr.name,
        "todo_name": None
    }

    if not pf_name:
        return
    process_flow_engine(to_close=to_close, to_open=to_open, process_flow_trace_info= process_flow_trace_info)
    if auto_stock:
        apply_workflow(pr, "Stock")

def stock_purchase_receipt(docname):

    pr = frappe.get_doc("Purchase Receipt", docname)
    if pr.is_internal_supplier == 1:
        return

    to_close = [{
        "doctype": "Purchase Receipt",
        "docname": docname,
    }]

    mrs = set()
    for item in pr.items:
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

def mirror_internal_pr(doc):
    if doc.is_internal_supplier:
        return
    
    mr_items_map = {}

    for item in doc.items:
        if not item.material_request:
            continue

        mr = item.material_request

        if mr not in mr_items_map:
            mr_items_map[mr] = {
                "sales_order": None,
                "purchase_order": None,
                "items": []
            }

        # 只保留 item_code 和 qty
        mr_items_map[mr]["items"].append({
            "item_code": item.item_code,
            "qty": item.received_qty
        })

    enrich_mr_items_map(mr_items_map)

    for mr, data in mr_items_map.items():
        po_name = data["purchase_order"]
        if not po_name:
            continue

        pr_doc = make_purchase_receipt(po_name)

        # 创建 MR item_code 集合，方便匹配
        mr_item_codes = {item["item_code"] for item in data["items"]}

        # 反向遍历 PR items，删除不在 MR 中的
        for i in range(len(pr_doc.items) - 1, -1, -1):
            pr_item = pr_doc.items[i]
            if pr_item.item_code in mr_item_codes:
                # 匹配到 MR 的 item，替换数量
                for mr_item in data["items"]:
                    if pr_item.item_code == mr_item["item_code"]:
                        pr_item.qty = mr_item["qty"]
                        break
            else:
                # 不在 MR 中，删除该行
                pr_doc.items.pop(i)

        pr_doc.save()
        #pr_doc.submit()
        

def enrich_mr_items_map(mr_items_map):

    for mr, data in list(mr_items_map.items()):
        # MR doc
        mr_doc = frappe.get_doc("Material Request", mr)

        # MR → SO
        for item in mr_doc.items:
            so_name = item.sales_order
            if so_name:
                break
            
        # SO → PO（内部）
        po_name = None
        if so_name:
            so_doc = frappe.get_doc("Sales Order", so_name)
            if so_doc.is_internal_customer and so_doc.inter_company_order_reference:
                po_name = so_doc.inter_company_order_reference

        # 回写结构
        mr_items_map[mr] = {
            "sales_order": so_name,
            "purchase_order": po_name,
            "items": data["items"]
        }

    return mr_items_map
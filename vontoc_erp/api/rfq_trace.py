import frappe
from frappe.utils import get_link_to_form

@frappe.whitelist()
def get_rfq_process_trace(docname):
    def build_history(doctype, name):
        doc_created = frappe.db.get_value(doctype, name, ["creation", "owner"], as_dict=1)
        versions = frappe.get_all("Version", 
            filters={"docname": name, "ref_doctype": doctype}, 
            fields=["data", "creation"], 
            order_by="creation asc")
        
        history = [{
            "workflow_state": "Draft",
            "timestamp": doc_created.creation
        }]
        
        for v in versions:
            data = frappe.parse_json(v.data)
            if data and data.get("changed"):
                for change in data["changed"]:
                    if change[0] == "workflow_state":
                        history.append({
                            "workflow_state": change[2],
                            "timestamp": v.creation
                        })
        return history

    def build_node(doctype, name):
        doc = frappe.get_doc(doctype, name)
        node = {
            "type": doctype,
            "name": name,
            "workflow_state": doc.get("workflow_state"),
            "history": build_history(doctype, name),
            "children": [],
            "item_price":[]
        }

        if doctype == "Request for Quotation":
            # 获取所有相关Supplier Quotation
            sqs = frappe.get_all("Supplier Quotation", 
                filters={"request_for_quotation": name}, 
                fields=["name"])
            
            for sq in sqs:
                node["children"].append(build_node("Supplier Quotation", sq["name"]))
                
                # 获取该SQ的所有Item Code
                sq_items = frappe.get_all("Supplier Quotation Item",
                    filters={"parent": sq["name"]},
                    fields=["item_code"],
                    distinct=True)
                
                # 为每个Item Code查找Item Price
                for item in sq_items:
                    item_prices = frappe.get_all("Item Price",
                    filters={"item_code": item["item_code"]},
                    fields=["name"])
                    for price in item_prices:
                        # 检查是否已存在相同 Item Price
                        if not any(p["type"] == "Item Price" and p["name"] == price["name"] for p in node["item_price"]):
                            node["item_price"].append({
                                "type": "Item Price",
                                "name": price["name"],
                                "workflow_state": "Created",  # Item Price 没有工作流状态
                                "history": [
                                ],
                                "children": []
                            })
        return node

    return build_node("Request for Quotation", docname)

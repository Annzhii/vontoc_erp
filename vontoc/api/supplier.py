import frappe

def create_customer_from_supplier(supplier_name, company):

    supplier = frappe.get_doc("Supplier", supplier_name)
    customer = frappe.new_doc("Customer")
    customer.customer_name = supplier.supplier_name
    customer.customer_type = "Company"
    customer.default_currency = "CNY"
    customer.default_price_list = "Cost Price"

    if supplier.supplier_primary_address:
        customer.customer_primary_address = supplier.supplier_primary_address

    if supplier.supplier_primary_contact:
        customer.customer_primary_contact = supplier.supplier_primary_contact

    customer.insert(ignore_permissions=True)

    company_abbr = frappe.get_value("Company", company, "abbr")

    customer.append("accounts", {
        "company": company,
        "account": f"1311 - Debtors - CNY - {company_abbr}"
    })

    auto_map_addresses(supplier, customer)
    auto_map_contacts(supplier, customer)

    customer.save(ignore_permissions=True)

def auto_map_addresses(supplier, customer):
    addresses = frappe.get_all(
        "Dynamic Link",
        filters={
            "link_doctype": "Supplier",
            "link_name": supplier.name,
            "parenttype": "Address"
        },
        fields=["parent"]
    )

    if addresses:
        for address in addresses:
            supplier_address = frappe.get_doc("Address", address.parent)

            address = frappe.new_doc("Address")

            address.address_title = customer.customer_name
            address.address_type = "Billing"

            address.address_line1 = supplier_address.address_line1
            address.address_line2 = supplier_address.address_line2
            address.city = supplier_address.city
            address.state = supplier_address.state
            address.country = supplier_address.country
            address.pincode = supplier_address.pincode

            address.append("links", {
                "link_doctype": "Customer",
                "link_name": customer.name
            })

            address.insert(ignore_permissions=True)

def auto_map_contacts(supplier, customer):
    contacts = frappe.get_all(
        "Dynamic Link",
        filters={
            "parenttype": "Contact",
            "link_doctype": "Supplier",
            "link_name": supplier.name
        },
        fields=["parent"]
    )

    if contacts:
        supplier_contacts = frappe.get_doc(
            "Contact",
            contacts[0]["parent"]
        )

        for supplier_contact in supplier_contacts:
            contact = frappe.new_doc("Contact")

            contact.first_name = supplier_contact.first_name
            contact.last_name = supplier_contact.last_name

            contact.email_ids = []
            for email in supplier_contact.email_ids:
                contact.append("email_ids", {
                    "email_id": email.email_id,
                    "is_primary": email.is_primary
                })

            supplier_contact = frappe.get_doc("Contact", "CON-00001")

            contact.phone_nos = []
            for phone in supplier_contact.phone_nos:
                contact.append("phone_nos", {
                    "phone": phone.phone,
                    "is_primary_phone": phone.is_primary_phone
                })

            contact.append("links", {
                "link_doctype": "Customer",
                "link_name": customer.name
            })

            contact.insert(ignore_permissions=True)

def create_supplier_warehouse(doc, method=None):

    company = frappe.defaults.get_user_default("Company")

    # 防止重复创建
    if frappe.db.exists(
        "Warehouse",
        {
            "warehouse_name": ["like", f"{doc.supplier_name}%"],
            "company": company
        }
    ):
        return

    # 找 Supplier Group
    supplier_group = frappe.db.get_value(
        "Warehouse",
        {
            "company": company,
            "warehouse_name": "Supplier",
            "is_group": 1,
        },
        "name"
    )

    if not supplier_group:
        frappe.throw(
            "Supplier warehouse group not found"
        )

    warehouse = frappe.get_doc({
        "doctype": "Warehouse",
        "warehouse_name": doc.supplier_name,
        "parent_warehouse": supplier_group,
        "company": company,
        "is_group": 0,
    })

    warehouse.insert(ignore_permissions=True)
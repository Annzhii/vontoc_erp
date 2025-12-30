app_name = "vontoc"
app_title = "VONTOC"
app_publisher = "anzhi"
app_description = "Vontoc"
app_email = "info@vontoc.com"
app_license = "mit"

fixtures = [
"Client Script",
"Workflow",
"Workflow State",
"Property Setter",
"Document Naming Rule",
"Report",
"Letter Head",
"Print Settings",
"Workflow Action Master",
"CRM Form Script"]

# 把Supplier Quotation Comparison 报告的的python文件替换为custom app里面python文件
doctype_js = {
    #"Delivery Note": "public/js/delivery_note.js",
    #"Sales Order": "public/js/sales_order.js",
    "Shipment": "public/js/shipment.js"
}

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "vontoc",
# 		"logo": "/assets/vontoc/logo.png",
# 		"title": "VONTOC",
# 		"route": "/vontoc",
# 		"has_permission": "vontoc.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/vontoc/css/vontoc.css"
# app_include_js = "/assets/vontoc/js/vontoc.js"


# include js, css files in header of web template
# web_include_css = "/assets/vontoc/css/vontoc.css"
# web_include_js = "/assets/vontoc/js/vontoc.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "vontoc/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "vontoc/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "vontoc.utils.jinja_methods",
# 	"filters": "vontoc.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "vontoc.install.before_install"
# after_install = "vontoc.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "vontoc.uninstall.before_uninstall"
# after_uninstall = "vontoc.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "vontoc.utils.before_app_install"
# after_app_install = "vontoc.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "vontoc.utils.before_app_uninstall"
# after_app_uninstall = "vontoc.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "vontoc.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "ToDo": "vontoc.api.todo.get_permission_query_conditions"
}
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    #"Payment Entry": "vontoc.api.overrides.VONTOCPaymentEntry",
    "Purchase Order": "vontoc.api.overrides.VONTOCPurchaseOrder",
    "Purchase Receipt": "vontoc.api.overrides.VONTOCPurchaseReceipt",
    #"Purchase Invoice": "vontoc.api.overrides.VONTOCPurchaseInvoice",
    #"Payment Request": "vontoc.api.overrides.VONTOCPaymentRequest",
    #"Payment Entry": "vontoc.api.overrides.VONTOCPaymentEntry",
    #"Sales Order": "vontoc.api.overrides.VONTOCSalesOrder",
    "Sales Invoice": "vontoc.api.overrides.VONTOCSalesInvoice",
    "Delivery Note": "vontoc.api.overrides.VONTOCDeliveryNote",   
    "Material Request": "vontoc.api.overrides.VONTOCMaterialRequest", 
    "Subcontracting Receipt": "vontoc.api.overrides.VONTOCSubcontractingReceipt",
    "Subcontracting Order": "vontoc.api.overrides.VONTOCSubcontractingOrder",
 	#"ToDo": "custom_app.overrides.CustomToDo"
    "Item": "vontoc.api.overrides.VONTOCItem",
    "Supplier Quotation": "vontoc.api.overrides.VONTOCSupplierQuotation",
    "Guideline Price": "vontoc.api.overrides.VONTOCGuidelinePrice",
    "Shipment": "vontoc.api.overrides.VONTOCShipment",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
    "Item": {
        "before_save": "vontoc.event.item.auto_rename_on_group_change",
    },
    "Communication": {
        # event 负责推送push notification， api负责内部 notify_user
        "after_insert": ["vontoc.event.communication.communication_after_insert", "vontoc.api.communication.after_insert_communication"]
    }
}

# Scheduled Tasks
# ---------------
scheduler_events = {
    "cron": {
        "0/1 * * * *": [
            "frappe.email.doctype.email_account.email_account.pull"
        ]
    }
}

# scheduler_events = {
# 	"all": [
# 		"vontoc.tasks.all"
# 	],
# 	"daily": [
# 		"vontoc.tasks.daily"
# 	],
# 	"hourly": [
# 		"vontoc.tasks.hourly"
# 	],
# 	"weekly": [
# 		"vontoc.tasks.weekly"
# 	],
# 	"monthly": [
# 		"vontoc.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "vontoc.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
    #"frappe.desk.doctype.event.event.get_events": "vontoc.event.get_events"
    "frappe.desk.form.assign_to.add": "vontoc.api.overrides_whitelist.add"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "vontoc.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["vontoc.utils.before_request"]
# after_request = ["vontoc.utils.after_request"]

# Job Events
# ----------
# before_job = ["vontoc.utils.before_job"]
# after_job = ["vontoc.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"vontoc.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


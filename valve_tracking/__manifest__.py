# Copyright 2022 Matt Taylor
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Valve Exchange Tracking",
    "summary": "Track exchanged products without the management overhead of inventory or invoices.",
    "version": "15.0.1.0.0",
    "development_status": "Beta",
    "author": "Matt Taylor",
    "website": "https://github.com/matt454357/lindenel-odoo-custom",
    'category': 'Invoices & Payments',
    "depends": [
        'base',
        'product',
        'hr',
        'mail',
        'web_m2x_options',
        'barcodes',
        'barcode_font',
    ],
    "license": "AGPL-3",
    'assets': {
        'web.assets_backend': [
            '/valve_tracking/static/src/js/move_barcode_handler.js',
        ]
    },
    "data": [
        "data/ir_sequence_data.xml",
        "data/product_category_data.xml",
        "data/hr_department_data.xml",
        "security/ir.model.access.csv",
        "views/valve_move_views.xml",
        "views/valve_repair_views.xml",
        "views/valve_serial_views.xml",
        "views/qb_invoice_views.xml",
        "views/product_template_views.xml",
        # "wizards/wizard_valve_move_in_scan_views.xml",
        "wizards/wizard_valve_move_in_core_views.xml",
        "views/valve_tracking_menu_views.xml",
        "report/valve_report_core_tickets.xml",
        "report/valve_report_box_label.xml",
        "report/valve_report_repair_sheet.xml",
        "report/valve_report_repair_sheet_ship.xml",
        "report/valve_reports.xml",
    ],
    "installable": True,
    "auto_install": False,
}

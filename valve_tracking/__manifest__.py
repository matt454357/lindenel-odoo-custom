# Copyright 2022 Matt Taylor
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Exchange Core Tracking",
    "summary": "Track exchanged product cores without the management overhead of inventory or invoices.",
    "version": "15.0.1.0.0",
    "development_status": "Beta",
    "author": "Matt Taylor",
    "website": "https://github.com/matt454357/lindenel-odoo-custom",
    'category': 'Invoices & Payments',
    "depends": ['base', 'product', 'mail'],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "views/core_exchange_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}

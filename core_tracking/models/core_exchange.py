from odoo import models, fields, api
from odoo.exceptions import UserError
import re


class CoreExchange(models.Model):
    _name = 'core.exchange'
    _description = 'Core Exchange'
    _inherit = ['mail.thread']

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer",
        required=True,
    )

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        required=True,
    )

    description = fields.Char(
        string="Description",
        required=True,
    )

    quantity = fields.Integer(
        string="Qty",
        required=True,
        default=1,
    )

    invoice_date = fields.Date(
        string="Invoice Date",
        required=True,
    )

    is_paid = fields.Boolean(
        string="Paid",
        required=True,
        default=False,
    )

    ext_ref = fields.Char(
        string="Ext Ref",
    )

    qb_invoice = fields.Char(
        string="QB Invoice",
        required=True,
    )

    is_returned = fields.Boolean(
        string="Returned",
        compute="_compute_returned",
        store=True,
    )

    return_date = fields.Date(
        string="Return Date",
        tracking=True,
    )

    return_serial = fields.Char(
        string="Returned Serial",
        tracking=True,
    )

    @api.depends('return_date')
    def _compute_returned(self):
        for rec in self:
            is_returned = rec.return_date

    def action_return(self):
        pass

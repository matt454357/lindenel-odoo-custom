from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QbInvoice(models.Model):
    _name = 'qb.invoice'
    _description = 'QuickBooks Invoice'
    _inherit = ['mail.thread']
    _order = "name desc"
    _sql_constraints = [
        ('qb_ref_uniq', 'unique (qb_ref)', "QB TxnID must be unique"),
    ]

    name = fields.Integer(
        string="Invoice Num",
        required=True,
        copy=False,
        index=True,
    )
    qb_ref = fields.Char(
        string='QB TxnID',
        required=True,
        copy=False,
        index=True,
    )
    txn_date = fields.Date(
        string='Invoice Date',
        required=True,
        copy=False,
    )
    ship_date = fields.Date(
        string='Ship Date',
        copy=False,
    )
    is_paid = fields.Boolean(
        string="Paid",
        required=True,
        default=False,
        copy=False,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer",
        required=True,
        copy=False,
    )
    ship_method = fields.Char(
        string="Ship Via",
        copy=False,
    )
    po_number = fields.Char(
        string="Customer PO",
        copy=False,
    )
    qb_invoice_line_ids = fields.One2many(
        comodel_name='qb.invoice.line',
        inverse_name='qb_invoice_id',
        string="Lines",
    )

    ship_addr1 = fields.Char(
        string="Ship1",
    )
    ship_addr2 = fields.Char(
        string="Ship2",
    )
    ship_addr3 = fields.Char(
        string="Ship3",
    )
    ship_addr4 = fields.Char(
        string="Ship4",
    )
    ship_addr5 = fields.Char(
        string="Ship5",
    )
    ship_city = fields.Char(
        string="Ship City",
    )
    ship_state = fields.Char(
        string="Ship State",
    )
    ship_zip = fields.Char(
        string="Ship ZIP",
    )
    ship_country = fields.Char(
        string="Ship Country",
    )
    ship_address = fields.Text(
        string="Ship Address",
        compute="_compute_ship_address",
        store=True,
    )

    @api.depends('ship_addr1', 'ship_addr2', 'ship_addr3', 'ship_addr4', 'ship_addr5', 'ship_city', 'ship_state',
                 'ship_zip', 'ship_country')
    def _compute_ship_address(self):
        for rec in self:
            address_items = []
            if rec.ship_addr1:
                address_items.append(rec.ship_addr1)
            if rec.ship_addr2:
                address_items.append(rec.ship_addr2)
            if rec.ship_addr3:
                address_items.append(rec.ship_addr3)
            if rec.ship_addr4:
                address_items.append(rec.ship_addr4)
            if rec.ship_addr5:
                address_items.append(rec.ship_addr5)
            address = ""
            if address_items:
                address = "\n".join(address_items)
            if rec.ship_city or rec.ship_state or rec.ship_zip:
                address += "\n%s, %s %s" % (rec.ship_city or "<>", rec.ship_state or "<>", rec.ship_zip or "<>")
            if rec.ship_country:
                address += "\n%s" % rec.ship_country
            rec.ship_address = address

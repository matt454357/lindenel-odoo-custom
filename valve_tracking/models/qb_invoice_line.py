from odoo import models, fields, api


class QbInvoice(models.Model):
    _name = 'qb.invoice.line'
    _description = 'QuickBooks Invoice Line'
    _sql_constraints = [
        ('qb_ref_uniq', 'unique (qb_ref)', "InvoiceLineTxnLineID must be unique"),
    ]

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        copy=False,
        readonly=True,
    )
    qb_invoice_id = fields.Many2one(
        comodel_name='qb.invoice',
        string='Invoice',
        required=True,
        copy=False,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        related='qb_invoice_id.partner_id',
        string='Customer',
        store=True,
    )
    ship_date = fields.Date(
        string='Ship Date',
        related='qb_invoice_id.ship_date',
        store=True,
    )
    qb_ref = fields.Char(
        string='InvoiceLineTxnLineID',
        required=True,
        index=True,
        copy=False,
    )
    qb_line_seq_num = fields.Integer(
        string='InvoiceLineSeqNo',
        required=True,
        copy=False,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Sent Product',
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
    valve_serial_id = fields.Many2one(
        comodel_name='valve.serial',
        string="LEI Serial",
        copy=False,
    )

    @api.depends('qb_invoice_id', 'product_tmpl_id')
    def _compute_name(self):
        for rec in self:
            rec.name = "[%s] %s" % (rec.qb_invoice_id.name, rec.product_tmpl_id.name)

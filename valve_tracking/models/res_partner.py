from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _sql_constraints = [
        ('qb_ref_uniq', 'unique (qb_ref)', "QuickBooks Reference must be unique"),
    ]

    qb_ref = fields.Char(
        string='QB Ref',
        index=True,
    )

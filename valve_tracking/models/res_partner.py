from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    _qb_ref_uniq = models.Constraint(
        'unique (qb_ref)',
        'QuickBooks Reference must be unique',
    )

    qb_ref = fields.Char(
        string='QB Ref',
        index=True,
    )

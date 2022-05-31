from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    qb_ref = fields.Char(string='Reference', index=True)

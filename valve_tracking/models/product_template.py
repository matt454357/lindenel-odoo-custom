from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qb_ref = fields.Char(string='Reference', index=True)

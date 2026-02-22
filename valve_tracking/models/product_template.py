from odoo import api, fields, models, tools


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @tools.ormcache()
    def _get_default_category_id(self):
        # Deletion forbidden (at least through unlink)
        return self.env.ref('valve_tracking.prod_cat_valves')

    qb_ref = fields.Char(
        string='QB Reference',
        index=True,
        readonly=True,
    )

    info_url = fields.Char(
        string="Info URL"
    )

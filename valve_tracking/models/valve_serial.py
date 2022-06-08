from odoo import models, fields, api
from odoo.exceptions import UserError
import re


class ValveSerial(models.Model):
    _name = 'valve.serial'
    _description = 'Valve Serial'
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "LEI Serial must be unique"),
        ('mfg_serial_uniq', 'unique (mfg_serial)', "MFG Serial must be unique"),
    ]

    name = fields.Char(
        string='LEI Serial',
        # required=True,
        copy=False,
        index=True,
        tracking=True,
        help="LEI Serial must be 4 to 6 digits, only numbers, and no spaces",
    )
    get_next_serial = fields.Boolean(
        string='Get Next',
        required=True,
        default=False,
    )
    mfg_serial = fields.Char(
        string='MFG Serial',
        # required=True,
        copy=False,
        index=True,
        tracking=True,
    )
    get_dummy_mfg_serial = fields.Boolean(
        string='Get Dummy',
        required=True,
        default=False,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Valve',
        required=True,
        tracking=True,
    )

    move_ids = fields.One2many(
        comodel_name='valve.move',
        inverse_name='valve_serial_id',
        readonly=True,
    )
    repair_ids = fields.One2many(
        comodel_name='valve.repair',
        inverse_name='valve_serial_id',
        readonly=True,
    )

    @api.model
    def create(self, vals):
        if vals.get('get_next_serial'):
            vals['name'] = self.env['ir.sequence'].next_by_code('lei.serial')
            vals['get_next_serial'] = False
        else:
            if vals['name']:
                # remove all whitespace
                vals['name'] = re.sub(r'\s+', '', vals['name'])
        if vals.get('get_dummy_mfg_serial'):
            vals['mfg_serial'] = self.env['ir.sequence'].next_by_code('na.mfg.serial')
            vals['get_dummy_mfg_serial'] = False
        else:
            if vals['mfg_serial']:
                # remove leading and trailer whitespace
                vals['mfg_serial'] = re.sub(r'^\s+|\s+$', '', vals['mfg_serial'])
                # reduce internal whitespace to a single space character
                vals['mfg_serial'] = re.sub(r'\s+', ' ', vals['mfg_serial'])
        res = super(ValveSerial, self).create(vals)
        return res

    @api.constrains('name')
    def _constrain_name(self):
        re_pattern = re.compile(r'^(\d{4,6})$')
        for rec in self:
            if not re.match(re_pattern, rec.name):
                message = f'"{rec.name}" Is Invalid.\n' \
                          f'LEI Serial must be 4 to 6 digits, all numbers, and no spaces.'
                raise UserError(message)

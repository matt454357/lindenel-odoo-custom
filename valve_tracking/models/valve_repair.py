from odoo import models, fields, api
from odoo.exceptions import UserError


class ValveRepair(models.Model):
    _name = 'valve.repair'
    _description = 'Valve Repair'
    _inherit = ['mail.thread']

    valve_serial_id = fields.Many2one(
        comodel_name='valve.serial',
        string="LEI Serial",
        required=True,
    )
    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done'),
            ('cancel', 'Canceled'),
        ],
        string='Status',
        readonly=True,
        index=True,
        copy=False,
        default='draft',
        tracking=True,
    )
    repair_date = fields.Date(
        string='Repair Date',
        default=fields.Date.today(),
        copy=False,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Sent Product',
        related='valve_serial_id.product_tmpl_id',
    )
    repair_comments = fields.Char(
        string="Repair Comments",
        copy=False,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
    )

    disassemble_emp_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Disassembled',
        copy=False,
    )
    cleaned_emp_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Cleaned',
        copy=False,
    )
    assemble_emp_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Assembled',
        copy=False,
    )

    @api.depends('valve_serial_id', 'repair_date')
    def _compute_name(self):
        for rec in self:
            rec.name = "[%s] %s" % (rec.valve_serial_id.name, rec.repair_date.strftime("%Y-%m-%d"))

    def action_done(self):
        for rec in self:
            if all([rec.disassemble_emp_id, rec.cleaned_emp_id, rec.assemble_emp_id]):
                rec.state = 'done'
            else:
                raise UserError("Can't complete repair record without employee assignments")

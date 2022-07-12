from odoo import models, fields, api
from odoo.exceptions import UserError


class ValveRepair(models.Model):
    _name = 'valve.repair'
    _description = 'Valve Repair'
    _inherit = ['mail.thread']
    _order = 'repair_date desc'

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
    repair_comments = fields.Text(
        string="Repair Comments",
        copy=False,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
    )
    in_move_id = fields.Many2one(
        comodel_name='valve.move',
        string='Return Move',
        domain="[('move_type', '=', 'in')]",
        copy=False,
    )

    disassemble_emp_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Disassembled',
        domain=lambda self: [('department_id', '=', self.env.ref('valve_tracking.hr_dept_current').id)],
        copy=False,
    )
    cleaned_emp_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Cleaned',
        domain=lambda self: [('department_id', '=', self.env.ref('valve_tracking.hr_dept_current').id)],
        copy=False,
    )
    assemble_emp_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Assembled',
        domain=lambda self: [('department_id', '=', self.env.ref('valve_tracking.hr_dept_current').id)],
        copy=False,
    )
    test_emp_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Tested',
        domain=lambda self: [('department_id', '=', self.env.ref('valve_tracking.hr_dept_current').id)],
        copy=False,
    )
    pack_weight = fields.Float(
        string='Weight',
        copy=False,
    )

    qb_invoice_id = fields.Many2one(
        comodel_name='qb.invoice',
        string='QB Invoice',
        copy=False,
    )
    qb_invoice_line_id = fields.Many2one(
        comodel_name='qb.invoice.line',
        string='QB Invoice Line',
        copy=False,
    )

    @api.depends('valve_serial_id', 'repair_date')
    def _compute_name(self):
        for rec in self:
            rec.name = "[%s] %s" % (rec.valve_serial_id.name, rec.repair_date.strftime("%Y-%m-%d"))

    def action_done(self):
        for rec in self:
            if all([rec.disassemble_emp_id, rec.cleaned_emp_id, rec.assemble_emp_id, rec.test_emp_id]):
                rec.state = 'done'
            else:
                raise UserError("Can't complete repair record without employee assignments")

    def action_print_box_label(self):
        self.ensure_one()
        if self.state != 'done':
            raise UserError("You must complete the repair before printing the box label")
        if not self.pack_weight:
            raise UserError("You must enter a weight before printing the box label")
        return self.env.ref('valve_tracking.report_valve_box_label').report_action(self)

    def action_set_to_draft(self):
        self.ensure_one()
        if self.state != 'cancel':
            raise UserError("Repair must first be cancelled")
        self.state = 'draft'
        return True

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
        return True


from odoo import fields, models, api
from odoo.exceptions import UserError


class WizardValveMoveInCore(models.TransientModel):
    _name = "wizard.valve.move.in.core"
    _description = "Inbound Core Move"

    core_move_id = fields.Many2one(
        comodel_name='valve.move',
        string='Core Shipment',
        required=True,
    )
    valve_serial_id = fields.Many2one(
        comodel_name='valve.serial',
        string='Serial',
        related='core_move_id.valve_serial_id',
        readonly=True,
    )
    move_type = fields.Char(
        string='Move Type',
        required=True,
        default='in',
        readonly=True,
    )
    type_code = fields.Selection(
        string='Type Code',
        related='core_move_id.type_code',
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        related='core_move_id.partner_id',
        readonly=True,
    )
    core_track_num = fields.Char(
        string="Core Track Num",
        required=True,
    )

    @api.onchange('core_track_num')
    def _onchange_core_track_num(self):
        if self.core_track_num:
            core_out_move = self.env['valve.move'].search([
                ('core_track_num', '=', self.core_track_num),
                ('move_type', '=', 'out'),
            ])
            if core_out_move:
                self.core_move_id = core_out_move
            else:
                raise UserError("No core found with that tracking number")

    def action_complete(self):
        move_id = self.env['valve.move'].create({
            'valve_serial_id': self.valve_serial_id.id,
            'move_type': self.move_type,
            'type_code': self.type_code,
            'partner_id': self.partner_id.id,
            'core_track_num': self.core_track_num,
        })
        action = self.env.ref('valve_tracking.action_valve_move_in').sudo().read()[0]
        action['res_id'] = move_id.id
        return action

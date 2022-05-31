from odoo import fields, models
from odoo.exceptions import UserError


class WizardValveMoveInScan(models.TransientModel):
    _name = "wizard.valve.move.in.scan"
    _description = "Scan Inbound Valve Move"
    _inherit = 'barcodes.barcode_events_mixin'

    scan_error = fields.Boolean('Barcode Error')
    scan_name = fields.Char('Barcode Value')

    core_move_id = fields.Many2one(
        comodel_name='valve.move',
        string='Core Shipment',
        readonly=True,
    )
    valve_serial_id = fields.Many2one(
        comodel_name='valve.serial',
        string='Serial',
    )
    move_type = fields.Char(
        string='Move Type',
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
        related='core_move_id.core_track_num',
        readonly=True,
    )

    def barcode_scanned_action(self, barcode):
        core_out_move = self.env['valve.move'].search([('core_track_num', '=', barcode)])
        if core_out_move:
            self.core_move_id = core_out_move
            self.move_type = 'in'
        else:
            self.core_move_id = False
            self.move_type = False
            scan_wizard = self.create({'scan_error': True, 'scan_name': barcode})
            view_id = self.env.ref('valve_tracking.wizard_valve_move_in_scan_form').id
            return {
                'type': 'ir.actions.act_window',
                'name': "Scan Inbound Valve Move",
                'res_model': 'wizard.valve.move.in.scan',
                'target': 'current',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': scan_wizard.id,
                'context': {'form_view_initial_mode': 'edit', 'barcode_scan': True},
                'views': [[view_id, 'form']],
            }

    def action_complete(self):
        move_id = self.env['valve.move'].create({
            'valve_serial_id': self.valve_serial_id,
            'move_type': self.move_type,
            'type_code': self.type_code,
            'partner_id': self.partner_id,
            'core_track_num': self.core_track_num,
        })
        action = self.env.ref('valve_tracking.action_valve_move_in').read()[0]
        action['res_id'] = move_id.id
        return action

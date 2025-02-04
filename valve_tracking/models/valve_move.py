from odoo import models, fields, api
from odoo.exceptions import UserError


class ValveMove(models.Model):
    _name = 'valve.move'
    _description = 'Valve Move'
    _inherit = ['mail.thread']
    _order = 'move_date desc'

    name = fields.Char(
        string="Move Number",
        required=True,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('valve.move.number'),
        copy=False,
    )
    move_type = fields.Selection(
        selection=[
            ('in', 'In'),
            ('out', 'Out'),
        ],
        string='Move Type',
        required=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('waiting', 'Waiting'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        required=True,
        default='draft',
        copy=False,
        index=True,
        readonly=True,
        tracking=True,
        help=" * Draft: The move is not confirmed yet\n"
             " * Waiting: Done, but waiting for a return move (to or from customer)\n"
             " * Done: Not waiting on anything else\n"
             " * Cancelled: Someone cancelled this move, did we duplicate it?",
    )
    move_return_ids = fields.Many2many(
        comodel_name='valve.move',
        relation='valve_move_return_rel',
        column1='valve_move_id',
        column2='valve_return_id',
        string='Return Move',
        copy=False,
    )
    move_date = fields.Date(
        string="Move Date",
        required=True,
        default=lambda self: fields.Date.today(),
        copy=False,
    )
    valve_serial_id = fields.Many2one(
        comodel_name='valve.serial',
        string="LEI Serial",
        required=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        related='valve_serial_id.product_tmpl_id',
        string='Valve',
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        required=True,
    )
    is_warranty = fields.Boolean(
        string='Possible Warranty',
        required=True,
        default=False,
    )
    type_code = fields.Selection(
        selection=[
            ('r', '[R] Repair & Return'),
            ('c', '[C] Core Exchange'),
            ('3', '[3] 3 for 1 Exchange'),
            ('d', '[D] Donated'),
            ('a', '[A] Account Credit'),
            ('s', '[S] Outright Sale'),
        ],
        string="Type Code",
        required=True,
    )
    qb_invoice_line_id = fields.Many2one(
        comodel_name='qb.invoice.line',
        string='QB Invoice Line',
        index=True,
        copy=False,
    )
    qb_invoice_id = fields.Many2one(
        comodel_name='qb.invoice',
        related='qb_invoice_line_id.qb_invoice_id',
        string='QB Invoice',
        store=True,
        copy=False,
    )
    ship_address = fields.Text(
        comodel_name='qb.invoice',
        related='qb_invoice_line_id.qb_invoice_id.ship_address',
        string='Ship Address',
        store=True,
        copy=False,
    )
    ship_method = fields.Char(
        related='qb_invoice_line_id.qb_invoice_id.ship_method',
        string="Shipping",
        store=True,
        copy=False,
    )
    core_track_num = fields.Char(
        string="Core Track Num",
        copy=False,
        help="Core Tracking Number is composed of <LEI Serial><Move Number>",
    )
    track_code128 = fields.Char(
        string="Code128 Encoded Name",
        compute="_compute_code128",
        store=True,
    )
    repair_in_ids = fields.One2many(
        comodel_name='valve.repair',
        inverse_name='in_move_id',
        string='Repairs',
        readonly=True,
    )
    repair_out_id = fields.Many2one(
        comodel_name='valve.repair',
        string='Repair',
        # readonly=True,
    )
    comments = fields.Text(
        string="Comments",
        copy=False,
    )

    def parse_core_track_num(self, track_num):
        serial_num = 0
        move_num = 0
        if len(track_num) == 11:
            move_num = track_num[6:11] or 0
            serial_num = track_num[0:6] or 0
        if len(track_num) == 10:
            move_num = track_num[5:10] or 0
            serial_num = track_num[0:5] or 0
        return serial_num, move_num

    @api.depends('valve_serial_id', 'name')
    def _compute_code128(self):
        for rec in self:
            rec.track_code128 = self.env['barcode.nomenclature'].get_code128_encoding(f"{rec.valve_serial_id.name}{rec.name}")

    @api.onchange('qb_invoice_id')
    def _onchange_qb_invoice_id(self):
        self.partner_id = self.qb_invoice_id.partner_id
        #self.write({'partner_id': self.qb_invoice_id.partner_id})

    @api.onchange('core_track_num')
    def _onchange_core_track_num(self):
        if self.core_track_num:
            sent_serial_num, sent_move_num = self.parse_core_track_num(self.core_track_num)
            sent_move = self.search([('name', '=', sent_move_num)])
            sent_serial = self.valve_serial_id.search([('name', '=', sent_serial_num)])
            if len(sent_move) == 1:
                self.partner_id = sent_move.partner_id
                self.type_code = sent_move.type_code
                self.is_warranty = sent_move.is_warranty

    def action_confirm(self):
        self.ensure_one()
        if self.move_type == 'out' and self.valve_serial_id.repair_ids.filtered(lambda x: x.state == 'draft'):
            raise UserError("You need to complete the repair record for this valve before shipping it")
        if self.move_type == 'out' and not self.qb_invoice_line_id:
            raise UserError("You must enter an invoice line before shipping a valve")
        if self.type_code in ['r', 'w']:
            # these always come in before they go out
            code_name = self.type_code == 'r' and 'Repair & Return' or 'Warranty'
            if self.move_type == 'in':
                self.message_post(body="Waiting for an outbound '%s'" % code_name)
                self.state = 'waiting'
            else:
                res = self.link_received_exchange()
                if res:
                    self.state = 'done'
                else:
                    self.message_post(body="Can't find an inbound '%s'. You should match it up manually." % code_name)
                    self.state = 'waiting'
        elif self.type_code == '3':
            # We don't know if '3 for 1 Exchange' will come in first, or go out
            # first, so we try to link it for either move_type.
            if self.move_type == 'in':
                res = self.link_sent_3_exchange()
                if res:
                    self.state = 'done'
                else:
                    self.message_post(body="Waiting for an inbound '3 for 1 Exchange'")
                    self.state = 'waiting'
            else:
                res = self.link_received_3_exchange()
                if res:
                    self.state = 'done'
                else:
                    self.message_post(body="Waiting for an inbound '3 for 1 Exchange'")
                    self.state = 'waiting'
        elif self.type_code == 'c':
            if self.move_type == 'in':
                res = self.link_sent_core()
                if res:
                    self.state = 'done'
                else:
                    self.message_post(body="Can't find a matching outbound 'Core Exchange'.  "
                                           "If you already entered the Core Tracking Number, "
                                           "you will have to match it up manually.")
                    self.state = 'waiting'
            else:
                self.core_track_num = "%s%s" % (self.valve_serial_id.name, self.name)
                self.message_post(body="Waiting for inbound 'Core Exchange'")
                self.state = 'waiting'
        elif self.type_code in ['d', 'a']:
            if self.move_type == 'in':
                self.state = 'done'
            else:
                raise UserError("Can't create outbound moves for types 'Donated' or 'Account Credit'")
        else:
            # this would only happen if we added a new type_code, but did not write the handling
            return False
        return True

    def link_received_exchange(self):
        # this method is for direct exchanges
        # i.e. we should have received the valve, now we are sending it back
        self.ensure_one()
        if len(self.move_return_ids) == 1:
            self.move_return_ids.state = 'done'
            return True
        matches = self.search([
            ('valve_serial_id', '=', self.valve_serial_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'waiting'),
            ('move_type', '=', 'in'),
            ('type_code', '=', self.type_code),
            ('id', '!=', self.id),
        ])
        if len(matches) == 1:
            self.move_return_ids = [(6, 0, [matches.id])]
            matches.state = 'done'
            return True
        return False

    def link_sent_3_exchange(self):
        """
        we are receiving any one of 3
        we may have already sent 1
        find the 1 outbound, and link it here
        if an outbound is found, and it has 3 done inbounds, set it to done
        """
        self.ensure_one()
        if self.move_return_ids:
            sent = self.move_return_ids
        else:
            sent = self.search([
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'waiting'),
                ('move_type', '=', 'out'),
                ('type_code', '=', self.type_code),
                ('id', '!=', self.id),
            ], order='move_date', limit=1)
        if sent:
            self.move_return_ids = [(6, 0, [sent.id])]
            # look for 2 other done receipts linked to the sent valve
            if len(sent.move_return_ids.filtered(lambda x: x.state == 'done')) == 2:
                sent.state = 'done'
            return True
        return False

    def link_received_3_exchange(self):
        """
        we are sending 1
        we may have already received 3
        find the 3 inbounds, and link them here
        if 3 inbounds are waiting, set this to done
        also set the inbounds to done
        """
        self.ensure_one()
        matches = self.move_return_ids
        if len(matches) < 3:
            matches |= self.search([
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'waiting'),
                ('move_type', '=', 'in'),
                ('type_code', '=', self.type_code),
                ('id', '!=', self.id),
            ], order='move_date', limit=3-len(self.move_return_ids))
        if matches:
            self.move_return_ids = [(6, 0, matches.ids)]
            matches.update({'state': 'done'})
            if len(matches) == 3:
                return True
        return False

    def link_sent_core(self):
        self.ensure_one()
        if not self.core_track_num:
            return False
        sent_serial_num, sent_move_num = self.parse_core_track_num(self.core_track_num)
        if sent_move_num:
            sent_move = self.search([('name', '=', sent_move_num)])
            if not sent_move:
                invoice_id = self.env['qb.invoice'].search([('name', '=', sent_move_num)])
                if invoice_id:
                    sent_move = self.search([('qb_invoice_id', '=', invoice_id[0].id)])
            if len(sent_move) == 1:
                self.move_return_ids = [(6, 0, [sent_move.id])]
                sent_move.state = 'done'
                return True
        return False

    def action_get_repair(self):
        self.ensure_one()
        if self.move_type != 'in':
            raise UserError("This is only for creating repairs from valve receipts")
        action = self.env['ir.actions.act_window']._for_xml_id('valve_tracking.action_valve_repair')
        # action = self.env.ref('valve_tracking.valve_repair_action_view_form').sudo().read()[0]
        action['view_mode'] = 'form'
        action['views'] = []
        if not self.repair_in_ids:
            repairs = self.env['valve.repair'].search([
                ('valve_serial_id', '=', self.valve_serial_id.id),
                ('repair_date', '>=', self.move_date),
                ('in_move_id', '=', False),
            ])
            if repairs:
                repairs.update({'in_move_id': self.id})
            else:
                action['context'] = {
                    'default_valve_serial_id': self.valve_serial_id.id,
                    'default_partner_id': self.partner_id.id,
                    'default_in_move_id': self.id,
                    # 'default_repair_comments': self.partner_id.name,
                }
                return action
        if len(self.repair_in_ids) > 1:
            action['view_mode'] = 'tree'
            action['domain'] = [('in_move_id', 'in', self.repair_in_ids.ids)]
        elif len(self.repair_in_ids) == 1:
            action['res_id'] = self.repair_in_ids[0].id
        return action

    def action_link_print_repair(self):
        self.ensure_one()
        if self.move_type != 'out':
            raise UserError("This is only for printing valve shipments")
        if not self.repair_out_id:
            repair = self.env['valve.repair'].search([
                ('valve_serial_id', '=', self.valve_serial_id.id),
                ('state', '=', 'draft')
            ])
            if not repair:
                raise UserError("No open repair found for this valve serial number")
            self.repair_out_id = repair
            repair.state = 'done'
        return self.env.ref('valve_tracking.report_valve_repair_sheet_ship').report_action(self)

    def action_print_core_ticket(self):
        self.ensure_one()
        if self.move_type != 'out':
            raise UserError("This is only for printing valve shipments")
        if self.state == 'draft':
            raise UserError("Complete the shipment before printing the core ticket")
        return self.env.ref('valve_tracking.report_valve_3_core_tickets').report_action(self)

    def action_set_to_draft(self):
        self.ensure_one()
        if self.state != 'cancel':
            raise UserError("Move must first be cancelled")
        self.state = 'draft'
        return True

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
        return True

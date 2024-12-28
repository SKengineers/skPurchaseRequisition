# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from datetime import datetime, date, time, timedelta
from odoo import models, fields, api, _


class PurchaseRequisition(models.Model):
    _name = 'purchase.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Purchase Requisition'

    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    department_id = fields.Many2one('hr.department', string='Department', compute='compute_by_employee', store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    requisition_responsible_id = fields.Many2one('res.users', string='Requisition Responsible',
                                                 compute='compute_by_employee', store=True, readonly=False)

    requisition_date = fields.Date(string='Requisition Date', default=fields.Date.context_today)
    receive_date = fields.Date(string='Receive Date')
    requisition_deadline_date = fields.Date(string='Requisition Deadline')

    purchase_order_ids = fields.Many2many('purchase.order')
    count_purchase_order = fields.Integer(string='Count Purchase Order', compute='compute_count', store=True)
    picking_ids = fields.Many2many('stock.picking')
    count_picking = fields.Integer(string='Count Internal Transfer', compute='compute_count', store=True)

    requisition_line_ids = fields.One2many('purchase.requisition.line', 'requisition_id')

    location_id = fields.Many2one('stock.location', string='Source Location')
    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
    picking_type_id = fields.Many2one('stock.picking.type', string='Internal Picking Type')

    confirm_by_id = fields.Many2one('res.users', string='Confirmed by')
    confirm_date = fields.Date(string='Confirmed Date')
    department_manager_id = fields.Many2one('res.users', string='Department Manager')
    department_approve_date = fields.Date(string='Department Approval Date')
    approve_by_id = fields.Many2one('res.users', string='Approve by')
    approve_date = fields.Date(string='Approve Date')
    reject_by_id = fields.Many2one('res.users', string='Rejected by')
    reject_date = fields.Date(string='Rejected Date')

    state = fields.Selection([
        ('new', 'New'),
        ('waiting_department', 'Waiting Department Approval'),
        ('waiting_ir', 'Waiting IR Approval'),
        ('approved', 'Approved'),
        ('purchase_created', 'Purchase Order Created'),
        ('receive', 'Received'),
        ('reject', 'Reject'),
        ('cancel', 'Cancel')
    ], string='State', default='new')

    @api.depends('purchase_order_ids', 'picking_ids')
    def compute_count(self):
        for rec in self:
            rec.count_purchase_order = len(rec.purchase_order_ids)
            rec.count_picking = len(rec.picking_ids)

    @api.depends('employee_id')
    def compute_by_employee(self):
        for record in self:
            employee = record.employee_id
            if employee:
                record.requisition_responsible_id = self._get_user_id(employee)
                record.department_id = self._get_department_id(employee)
            else:
                record.requisition_responsible_id = False
                record.department_id = False

    def _get_user_id(self, employee):
        return employee.user_id.id if employee.user_id else False

    def _get_department_id(self, employee):
        return employee.department_id.id if employee.department_id else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.requisition') or _('New')
        return super(PurchaseRequisition, self).create(vals_list)

    def action_confirm(self):
        for rec in self:
            if not rec.requisition_line_ids:
                raise UserError(_("Please fill in data for requisition line before confirm"))
            if rec.employee_id and rec.employee_id.destination_location_id:
                rec.destination_location_id = rec.employee_id.destination_location_id.id
            elif rec.department_id and rec.department_id.destination_location_id:
                rec.destination_location_id = rec.department_id.destination_location_id.id
            else:
                raise UserError(_("Please select destination location for Employee or Department"))
            internal_picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('default_location_dest_id', '=', rec.destination_location_id.id),
                ('company_id', '=', rec.company_id.id)
            ])
            if not internal_picking_type or len(internal_picking_type) > 1:
                raise UserError(_("Please check and create or setting Internal Picking Type for this Employee/Department"))
            rec.location_id = internal_picking_type.default_location_src_id.id
            rec.picking_type_id = internal_picking_type.id
            rec.confirm_by_id = self.env.user.id
            rec.confirm_date = datetime.today()
            rec.state = 'waiting_department'

    def action_cancel(self):
        for rec in self:
            rec.message_post(
                body='Purchase Requisition has been cancel by %s' % (self.env.user.name),
                message_type='notification',
            )
            rec.state = 'cancel'

    def action_department_approve(self):
        for rec in self:
            rec.department_manager_id = self.env.user.id
            rec.department_approve_date = datetime.today()
            rec.state = 'waiting_ir'

    def action_reject(self):
        action = self.env.ref('ag_purchase_requisition.wizard_reject_purchase_requisition_action_view').read()[0]
        return action

    def action_ir_approve(self):
        for rec in self:
            rec.approve_by_id = self.env.user.id
            rec.approve_date = datetime.today()
            rec.state = 'approved'

    def create_purchase_order(self):
        supplier_ids = self.requisition_line_ids.mapped('supplier_ids')
        for supp in supplier_ids:
            line_requisition = self.requisition_line_ids.filtered(lambda x: supp.id in x.supplier_ids.ids)
            purchase_order = self.env['purchase.order'].create({
                'partner_id': supp.id
            })
            for line in line_requisition:
                product_line = purchase_order.order_line.filtered(lambda x: x.product_id.id == line.product_id.id)
                if product_line:
                    product_line.product_qty += line.quantity
                else:
                    self.env['purchase.order.line'].create({
                        'product_id': line.product_id.id,
                        'name': line.product_id.display_name,
                        'product_qty': line.quantity,
                        'order_id': purchase_order.id
                    })
            self.purchase_order_ids = [(4, purchase_order.id)]

    def create_internal_picking(self):
        purchase_requisition_line = self.requisition_line_ids.filtered(lambda x: x.requisition_action == 'picking')
        product_ids = purchase_requisition_line.mapped('product_id')
        for pro in product_ids:
            line_requisition = self.requisition_line_ids.filtered(lambda x: x.product_id.id == pro.id)
            total_qty = sum(line_requisition.mapped('quantity'))
            stock_quant = self.env['stock.quant'].search([
                ('product_id', '=', pro.id),
                ('location_id', '=', self.location_id.id)
            ])
            available_qty = sum(stock_quant.mapped('quantity'))
            if available_qty < total_qty:
                difference = total_qty - available_qty
                if not pro.seller_ids:
                    raise UserError(_("Please setting vendor for Product %s, we need data to create purchase Order") % pro.display_name)
                supplier_id = pro.seller_ids[0].partner_id
                purchase = self.env['purchase.order'].create({
                    'partner_id': supplier_id.id
                })
                self.purchase_order_ids = [(4, purchase.id)]
                self.env['purchase.order.line'].create({
                    'product_id': pro.id,
                    'name': pro.display_name,
                    'product_qty': difference,
                    'order_id': purchase.id
                })
                picking = self.env['stock.picking'].create({
                    'picking_type_id': self.picking_type_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.destination_location_id.id,
                    'move_ids': [(0, 0, {
                        'name': pro.display_name,
                        'product_id': pro.id,
                        'product_uom': pro.uom_id.id,
                        'product_uom_qty': available_qty,
                        'location_id': self.location_id.id,
                        'location_dest_id': self.destination_location_id.id,
                    })],
                })
                self.picking_ids = [(4, picking.id)]
            if available_qty >= total_qty:
                picking = self.env['stock.picking'].create({
                    'picking_type_id': self.picking_type_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.destination_location_id.id,
                    'move_ids': [(0, 0, {
                        'name': pro.display_name,
                        'product_id': pro.id,
                        'product_uom': pro.uom_id.id,
                        'product_uom_qty': total_qty,
                        'location_id': self.location_id.id,
                        'location_dest_id': self.destination_location_id.id,
                    })],
                })
                self.picking_ids = [(4, picking.id)]


        return True

    def create_picking_purchase(self):
        for rec in self:
            rec.create_purchase_order()
            rec.create_internal_picking()
            rec.state = 'purchase_created'

    def action_received(self):
        for rec in self:
            rec.receive_date = datetime.today()
            rec.state = 'receive'

    def action_view_purchase_order(self):
        self.ensure_one()
        action = {
            'name': _("Purchase Order"),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'target': 'current',
        }
        purchase_order_ids = self.purchase_order_ids.ids
        if len(purchase_order_ids) == 1:
            purchase = purchase_order_ids[0]
            action['res_id'] = purchase
            action['view_mode'] = 'form'
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', purchase_order_ids)]
        return action

    def action_view_internal_transfer(self):
        self.ensure_one()
        action = {
            'name': _("Internal Transfer"),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'target': 'current',
        }
        stock_picking = self.picking_ids.ids
        if len(stock_picking) == 1:
            picking = stock_picking[0]
            action['res_id'] = picking
            action['view_mode'] = 'form'
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', stock_picking)]
        return action

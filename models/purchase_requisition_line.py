# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PurchaseRequisitionLine(models.Model):
    _name = 'purchase.requisition.line'

    requisition_id = fields.Many2one('purchase.requisition')
    requisition_action = fields.Selection([
        ('purchase', 'Purchase Order'),
        ('picking', 'Internal Picking')
    ], string='Requisition Action', default=None)

    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    supplier_ids = fields.Many2many('res.partner', string='Vendors')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.uom_id = self.product_id.uom_id.id
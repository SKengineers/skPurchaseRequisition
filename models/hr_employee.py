# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
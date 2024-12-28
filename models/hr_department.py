# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
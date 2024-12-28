# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, date, time, timedelta


class WizardRejectPurchaseRequisition(models.TransientModel):
    _name = 'wizard.reject.purchase.requisition'
    _description = "Reject Purchase Requisition"

    reason = fields.Text(string='Reason')

    def action_reject(self):
        purchase_requisition = self.env['purchase.requisition'].browse(self.env.context.get('active_id'))
        if purchase_requisition:
            purchase_requisition.state = 'reject'
            purchase_requisition.reject_by_id = self.env.user.id
            purchase_requisition.reject_date = date.today()
            purchase_requisition.message_post(
                body='Purchase Requisition has been rejected by %s and reason is: %s' % (self.env.user.name, self.reason),
                message_type='notification',
            )

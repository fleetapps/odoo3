# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    purchase_order_count = fields.Integer("Purchase Order Count", compute='_compute_purchase_order_count')

    @api.depends('line_ids')
    def _compute_purchase_order_count(self):
        for account in self:
            account.purchase_order_count = len(account.line_ids.move_line_id.purchase_line_id.order_id)

    def action_view_purchase_orders(self):
        self.ensure_one()
        purchase_orders = self.with_context(analytic_plan_id=self.plan_id.id).line_ids.move_line_id.purchase_line_id.order_id
        result = {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "domain": [['id', 'in', purchase_orders.ids]],
            "name": _("Purchase Orders"),
            'view_mode': 'list,form',
        }
        if len(purchase_orders) == 1:
            result['view_mode'] = 'form'
            result['res_id'] = purchase_orders.id
        return result

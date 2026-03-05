# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    expense_policy_tooltip = fields.Char(compute='_compute_expense_policy_tooltip')

    @api.depends_context('lang')
    @api.depends('reinvoice_policy')
    def _compute_expense_policy_tooltip(self):
        for product_template in self:
            if not product_template.can_be_expensed or not product_template.reinvoice_policy:
                product_template.expense_policy_tooltip = False
            elif product_template.reinvoice_policy == 'no':
                product_template.expense_policy_tooltip = _(
                    "Expenses of this category may not be added to a Sales Order."
                )
            elif product_template.reinvoice_policy == 'cost':
                product_template.expense_policy_tooltip = _(
                    "Expenses will be added to the Sales Order at their actual cost when posted."
                )
            elif product_template.reinvoice_policy == 'sales_price':
                product_template.expense_policy_tooltip = _(
                    "Expenses will be added to the Sales Order at their sales price (product price, pricelist, etc.) when posted."
                )

    @api.depends('can_be_expensed')
    def _compute_visible_reinvoice_policy(self):
        expense_products = self.filtered(lambda p: p.can_be_expensed)
        super(ProductTemplate, self - expense_products)._compute_visible_reinvoice_policy()
        visibility = self.env.user.has_group('hr_expense.group_hr_expense_user')
        for product_template in expense_products:
            if not product_template.visible_reinvoice_policy:
                product_template.visible_reinvoice_policy = visibility

    @api.depends('can_be_expensed')
    def _compute_reinvoice_policy(self):
        super()._compute_reinvoice_policy()
        self.filtered(lambda t: not t.can_be_expensed).reinvoice_policy = 'no'

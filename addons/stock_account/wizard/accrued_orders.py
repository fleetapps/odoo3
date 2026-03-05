from odoo import models, api


class AccountAccruedOrdersWizard(models.TransientModel):
    _inherit = 'account.accrued.orders.wizard'

    @api.model
    def _get_product_price_diff_account(self, product):
        price_diff_account = super()._get_product_price_diff_account(product)
        if product.cost_method == 'standard':
            price_diff_account = product.categ_id.property_price_difference_account_id
        return price_diff_account

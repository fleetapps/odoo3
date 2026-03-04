from odoo import models

class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    def precision_get(self, application):
        stackmap = self.env.cr.cache.get('account_disable_recursion_stack', {})
        if (
                stackmap.get('ignore_discount_precision') and application == 'Discount' or
                stackmap.get('ignore_quantity_precision') and application == 'Product Unit of Measure'
        ):
            return 100
        return super().precision_get(application)

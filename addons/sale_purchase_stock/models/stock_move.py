# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        if self.sale_line_id.analytic_distribution:
            res['analytic_distribution'] = self.sale_line_id.analytic_distribution
        return res

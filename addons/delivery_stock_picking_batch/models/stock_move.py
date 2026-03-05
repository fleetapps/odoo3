# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        if any(rule.propagate_carrier for rule in self.rule_id):
            origin_picking = self.move_orig_ids.picking_id
            if origin_picking.carrier_id:
                vals['carrier_id'] = origin_picking.carrier_id.id
        return vals

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    repair_order_count = fields.Integer(
        string="Repair Order Count",
        compute='_compute_repair_order_count',
    )
    repair_order_ids = fields.One2many('repair.order', 'partner_id', string='Repair Order')

    def _compute_repair_order_count(self):
        self.repair_order_count = 0
        if not self.env.user.has_group('stock.group_stock_user'):
            return

        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )

        repair_order_groups = self.env['repair.order']._read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            groupby=['partner_id'],
            aggregates=['__count'],
        )
        self_ids = set(self._ids)

        for partner, count in repair_order_groups:
            while partner:
                if partner.id in self_ids:
                    partner.repair_order_count += count
                partner = partner.parent_id

    def action_view_repair_orders(self):
        action = self.env['ir.actions.act_window']._for_xml_id('repair.action_repair_order_tree')
        action['context'] = {'default_partner_id': self.id}
        if self.repair_order_count <= 1:
            action['views'] = [(False, 'form')]
            repair_order_id = self.env['repair.order'].search_fetch(
                [('partner_id', 'in', self.ids)],
                ['id'],
            )
            action['res_id'] = repair_order_id.id
        else:
            action['domain'] = [('partner_id', 'child_of', self.id)]
        return action

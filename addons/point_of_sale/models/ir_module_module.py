from odoo import api, models


class IrModuleModule(models.Model):
    _inherit = ['ir.module.module', 'pos.load.mixin']
    _name = "ir.module.module"

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'state']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('name', '=', 'pos_settle_due')]

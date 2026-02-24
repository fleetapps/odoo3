from odoo import _, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if self.env.company.l10n_jo_edi_demo_mode:
            alerts['l10n_jo_edi_demo_mode'] = {
                'level': 'warning',
                'message': _(
                    "Demo mode is enabled. Post successful generation:"
                    "\na. To synchronise this invoice with JoFotara, please reset this invoice to draft and change the JoFotara State to \"To Send\" by going "
                    "to Invoices > Select the Invoice > Other Info. Subsequently, please uncheck the Demo Mode by going to Accounting > Configuration > "
                    "Settings > Demo Mode, before trying again."
                    "\nb. To revert this invoice, please go to > Reset to Draft > Delete."
                    ),
            }
        return alerts

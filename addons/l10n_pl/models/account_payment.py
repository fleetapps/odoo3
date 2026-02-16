from odoo import fields, models


class L10nPlAccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_pl_bank_verification_status = fields.Selection(
        selection=[
            ('valid', 'Valid'),
            ('not_required', 'Not required'),
            ('invalid', 'Invalid'),
            ('invalid_nip', 'Unknown VAT'),
            ('incomplete', 'VAT or bank account empty'),
        ],
        string="Status",
        readonly=True,
        default='not_required',
        tracking=True,
    )
    l10n_pl_bank_verification_timestamp = fields.Datetime("Timestamp", readonly=True)
    l10n_pl_bank_verification_request_id = fields.Char("Correlation ID", readonly=True)

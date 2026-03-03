from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    l10n_pl_bank_verification_status = fields.Selection(
        selection=[
            ('valid', 'Valid'),
            ('not_required', 'Not required'),
            ('invalid', 'Invalid'),
        ],
        readonly=True,
        default='not_required',
        tracking=True,
    )
    l10n_pl_bank_verification_timestamp = fields.Datetime(readonly=True)
    l10n_pl_bank_verification_request_id = fields.Char("Correlation ID", readonly=True)

    def _l10n_pl_status_at_date(self, date):
        self.ensure_one()
        if self.l10n_pl_bank_verification_timestamp and self.l10n_pl_bank_verification_timestamp.date() == date:
            return self.l10n_pl_bank_verification_status
        return 'unverified'

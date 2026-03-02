from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------
    l10n_pk_edi_is_fbr_registered = fields.Boolean(string='FBR Registered', default=False)

    def _l10n_pk_edi_is_valid_vat(self):
        self.ensure_one()
        if not self.vat:
            return False
        return len(self.vat) == 7 or len(self.vat) == 13

    def _group_by_error_code(self):
        self.ensure_one()
        if not all(self[field] for field in ('street', 'city', 'state_id', 'country_id')):
            return sorted((
                ('message', self.env._('Partner(s) should have a complete address, verify their Street, City, State and Country.')),
                ('error_code', 'l10n_pk_edi_partner_address_missing'),
                ('level', 'danger'),
            ))
        return False

    def _l10n_pk_edi_export_check(self):
        """Validate Invoice/Credit-Note for E-Invoicing compliance."""
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(lambda m: m._group_by_error_code()).items():
            if not error_tuple:
                continue
            temp_dict = dict(error_tuple)
            alert_vals.update({
                temp_dict['error_code']: {
                    'message': temp_dict['message'],
                    'level': temp_dict['level'],
                    'action': invalid_records._get_records_action(),
                    'action_text':  self.env._('View Product(s)'),
                },
            })
        return alert_vals

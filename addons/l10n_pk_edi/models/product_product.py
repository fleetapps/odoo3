import re

from odoo import fields, models

from ..data.l10n_pk_edi_data import TRANSACTION_TYPE, UOM_CODES

HS_CODE_REGEX = re.compile(r'^\d{4}\.\d{4}$')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    l10n_pk_edi_hs_code = fields.Char(string='HS Code(PK)', copy=False, help='Standardized code for international shipping and goods declaration.')
    l10n_pk_edi_uom_code = fields.Selection(selection=UOM_CODES, string='UoM Code(PK)', help='Unit of Measure(UoM) is a standard unit to express quantities of stock or products.')
    l10n_pk_edi_transaction_type = fields.Selection(selection=TRANSACTION_TYPE, string='Transaction Type(PK)', default='75', required=True)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _group_by_error_code(self):
        self.ensure_one()
        if any(not self[field] for field in ('l10n_pk_edi_hs_code', 'l10n_pk_edi_uom_code', 'l10n_pk_edi_transaction_type')):
            return (
                ('message', self.env._('Product(s) must have a HS Code, UoM Code and Transaction Type.')),
                ('error_code', 'product_value_missing'),
                ('level', 'danger'),
            )

        if self.l10n_pk_edi_hs_code and not HS_CODE_REGEX.match(self.l10n_pk_edi_hs_code):
            return (
                ('message', self.env._('Product(s) has an invalid HS Code. It must follow the format 0000.0000 (8 digits).')),
                ('error_code', 'product_hscode_invalid'),
                ('level', 'danger'),
            )

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

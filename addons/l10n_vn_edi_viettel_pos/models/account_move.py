# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_invoice_legal_documents(self, filetype, allow_fallback=False):
        if filetype == 'pdf' and (sinvoice_attachment := self.l10n_vn_edi_sinvoice_pdf_file_id):
            return {
                'filename': sinvoice_attachment.name,
                'filetype': 'pdf',
                'content': sinvoice_attachment.raw,
            }
        return super()._get_invoice_legal_documents(filetype, allow_fallback=allow_fallback)

    def _l10n_vn_edi_add_buyer_information(self, json_values):
        super()._l10n_vn_edi_add_buyer_information(json_values)

        # For Walk-In Customer, there is no address and buyerNotGetInvoice should be set to 1
        if self.partner_id == self.env.ref('l10n_vn_edi_viettel_pos.partner_walk_in_customer', raise_if_not_found=False):
            del json_values['buyerInfo']['buyerAddressLine']
            json_values['buyerInfo']['buyerNotGetInvoice'] = 1

    def _l10n_vn_edi_add_item_information(self, json_values):
        '''Overwrite item information for discount lines to make sure the discount is correctly displayed on the invoice'''

        super()._l10n_vn_edi_add_item_information(json_values)

        config_id = self.env['pos.config'].browse(self.env.context.get('config_id'))

        if not config_id._fields.get('discount_product_id'):
            return

        discount_product = config_id.discount_product_id
        if not discount_product:
            return

        code_map = {'product': 1, 'line_note': 2, 'discount': 3}
        for item, line in zip(json_values['itemInfo'], self.invoice_line_ids.filtered(lambda ln: ln.display_type in code_map)):
            if line.product_id == discount_product:
                item['selection'] = code_map['discount']
                item['isIncreaseItem'] = False
                item['unitPrice'] = abs(line.price_unit)
                item['quantity'] = abs(line.quantity)
                item['itemTotalAmountWithoutTax'] = abs(line.currency_id.round(line.price_unit * line.quantity))
                item['itemTotalAmountAfterDiscount'] = abs(line.price_subtotal)
                item['itemTotalAmountWithTax'] = abs(line.price_total)

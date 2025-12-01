from odoo import api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_l10n_es_edi_sii_document(self):
        """
        Prevents the deletion of attachments related to successful SII documents.
        """
        linked_docs = self.env['l10n_es_edi_sii.document'].sudo().search([
            ('attachment_id', 'in', self.ids),
            ('state', 'in', ('accepted', 'accepted_with_errors', 'cancelled'))
        ], limit=1)

        if linked_docs:
            raise UserError(self.env._("You can't unlink an attachment that is part of a sent SII document."))

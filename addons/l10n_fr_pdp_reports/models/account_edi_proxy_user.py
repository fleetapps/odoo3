from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('pdp', 'French PDP')], ondelete={'pdp': 'cascade'})

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        urls['pdp'] = {
            'demo': False,
            'prod': IrConfigParameter.get_param('l10n_fr_pdp_proxy_server_url_prod', 'https://pdp.api.odoo.com'),
            'test': IrConfigParameter.get_param('l10n_fr_pdp_proxy_server_url_test', 'https://pdp.test.odoo.com'),
        }
        return urls

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type != 'pdp':
            return super()._get_proxy_identification(company, proxy_type)
        vat = company.partner_id.vat
        if not vat:
            raise UserError(_("Please set the company VAT before enabling PDP proxy integration."))
        return vat

    def _l10n_fr_pdp_call_proxy(self, endpoint, params=None):
        self.ensure_one()
        if self.proxy_type != 'pdp':
            raise UserError(_("EDI user should be of type PDP."))
        params = params or {}
        try:
            return self._make_request(f'{self._get_server_url()}/{endpoint}', params=params)
        except AccountEdiProxyError as error:
            raise UserError(error.message or ("Failed to contact the PDP proxy.")) from error

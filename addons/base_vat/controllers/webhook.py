import logging

from odoo import http, SUPERUSER_ID
from odoo.http import request

from odoo.tools import consteq
from odoo.tools import hmac as hmac_tool

_logger = logging.getLogger(__name__)

WEBHOOK_UPDATE_VIES_ROUTE = '/base_vat/1/webhook_update_vies'


class BaseVatWebhookController(http.Controller):
    @http.route(WEBHOOK_UPDATE_VIES_ROUTE, type='jsonrpc', auth='public')
    def webhook_update_vies(self, secret, vat, status):
        """
        Webhook called by IAP when it updates a status from the pending state.
        The secret is computed by the Odoo db (in _compute_vies_valid) and stored
        on IAP such that only IAP can call this webhook.
        """
        if not consteq(hmac_tool(request.env(su=True), "vies", vat), secret):
            _logger.warning("VIES update failed: secret does not match.")
            return False

        partners = request.env["res.partner"].with_user(SUPERUSER_ID).search([("vat", "=", vat)])
        partners._update_vies_status(status)

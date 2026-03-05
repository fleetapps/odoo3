from odoo.addons.pos_bancontact_pay.controllers.webhook import BancontactPayController


class SelfOrderBancontactPayController(BancontactPayController):
    def _notify_pos(self, pos_payment, bancontact_status):
        super()._notify_pos(pos_payment, bancontact_status)

        order = pos_payment.pos_order_id
        error = self._get_bancontact_error_message(bancontact_status)
        order.config_id._notify(
            "FINALIZE_KIOSK_PAYMENT",
            {
                "status": "success" if bancontact_status == "SUCCEEDED" else "error",
                "order_id": order.id,
                "error": error,
            },
        )

    def _get_bancontact_error_message(self, bancontact_status):
        if bancontact_status == "CANCELLED":
            return "Payment cancelled"
        if bancontact_status == "EXPIRED":
            return "Payment expired"
        return None

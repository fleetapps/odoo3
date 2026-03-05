from werkzeug.exceptions import Unauthorized

from odoo import _, http

from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController


class PosSelfOrderControllerBancontactPay(PosSelfOrderController):
    @http.route("/pos-self-order/create-bancontact-pay-payment", auth="public", type="jsonrpc", website=True)
    def bancontact_pay_create_payment_from_kiosk(self, access_token, order_id, payment_id):
        pos_config = self._verify_pos_config(access_token)

        order = pos_config.env['pos.order'].browse(order_id)
        payment = order.payment_ids.filtered(lambda p: p.id == payment_id) if order else None
        payment_method = payment.payment_method_id if payment else None

        if not order or order.config_id.id != pos_config.id or \
            not payment or payment.pos_order_id.id != order.id or \
            not payment_method or pos_config.id not in payment_method.config_ids.ids or payment_method.payment_provider != 'bancontact_pay':
            raise Unauthorized()

        payment_method.sudo().create_bancontact_payment(
            payment_id=payment.id,
            amount=payment.amount,
            currency=payment.currency_id.name,
            description=_("Payment at %(company)s\nKiosk: %(config)s", company=pos_config.company_id.name, config=pos_config.name),
            usage=payment_method.bancontact_usage,
        )

        if payment.qr_code:
            payment.qr_code = f"{payment.qr_code}&s=M"

        return {
            'pos.order': pos_config.env['pos.order']._load_pos_self_data_read(order, pos_config),
            'pos.payment': pos_config.env['pos.payment']._load_pos_self_data_read(payment, pos_config),
        }

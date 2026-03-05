from odoo.tests.common import tagged

from odoo.addons.pos_bancontact_pay.tests.test_webhook import TestWebhook


@tagged("post_install", "-at_install")
class TestSelfOrderWebhook(TestWebhook):

    def test_bancontact_webhook_succeeded(self):
        pos_payment, payload = self._make_payment_and_payload("succeeded_id", "waitingScan", "succeeded_qr_code")

        with self._notify_patcher(pos_payment) as mock_notify:
            self._post_status(payload, "SUCCEEDED")
            self.assertEqual(pos_payment.pos_order_id.state, "draft")  # Paid later when /kiosk/payment is called --> _payment_request_from_kiosk
            self._assert_notify_finalize_kiosk_payment(mock_notify, pos_payment.pos_order_id.id, "SUCCEEDED")
            self._assert_notify_count(mock_notify, "FINALIZE_KIOSK_PAYMENT", 1)

    def test_bancontact_webhook_error(self):
        for bancontact_status in ("AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"):
            pos_payment, payload = self._make_payment_and_payload("error_id", "waitingScan", "error_qr_code")

            with self._notify_patcher(pos_payment) as mock_notify:
                self._post_status(payload, bancontact_status)
                self.assertEqual(pos_payment.pos_order_id.state, "draft")
                self._assert_notify_finalize_kiosk_payment(mock_notify, pos_payment.pos_order_id.id, bancontact_status)
                self._assert_notify_count(mock_notify, "FINALIZE_KIOSK_PAYMENT", 1)

    def _assert_notify_finalize_kiosk_payment(self, mock_notify, order_id, bancontact_status):
        error = None
        if bancontact_status == "CANCELLED":
            error = "Payment cancelled"
        elif bancontact_status == "EXPIRED":
            error = "Payment expired"

        expected_payload = {
            "status": "success" if bancontact_status == "SUCCEEDED" else "error",
            "order_id": order_id,
            "error": error,
        }
        self._assert_notify_with(mock_notify, "FINALIZE_KIOSK_PAYMENT", expected_payload)

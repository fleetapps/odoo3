import { patch } from "@web/core/utils/patch";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";

patch(PaymentPage.prototype, {
    async startPayment() {
        // Already waiting bancontact payment, do not start another one
        const payments = this.selfOrder.currentOrder.payment_ids;
        const waitingBancontactPayment = payments.find(
            (p) =>
                p.payment_method_id.id === this.state.paymentMethodId &&
                p.payment_method_id.payment_provider === "bancontact_pay" &&
                p.bancontact_id &&
                p.qr_code &&
                ["waiting", "waitingScan"].includes(p.payment_status)
        );
        if (waitingBancontactPayment) {
            this.state.qrCode = waitingBancontactPayment.qr_code;
            return;
        }
        await super.startPayment(...arguments);
    },
});

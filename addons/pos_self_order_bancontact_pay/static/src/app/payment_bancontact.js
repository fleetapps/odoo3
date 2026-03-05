import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentBancontact } from "@pos_bancontact_pay/app/payment_bancontact";
import { rpc } from "@web/core/network/rpc";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentBancontact.prototype, {
    async sendPaymentRequest(line) {
        if (this.pos.kioskMode) {
            try {
                const order = await this.pos.sendDraftOrderToServer();
                const data = await rpc(`/pos-self-order/create-bancontact-pay-payment`, {
                    access_token: this.pos.access_token,
                    order_id: order.id,
                    payment_id: line.id,
                });
                this.pos.models.connectNewData(data);
            } catch (error) {
                this._showError(error);
                throw error;
            }
            return true;
        }
        return await super.sendPaymentRequest(...arguments);
    },

    _showError(error) {
        if (error?.data?.message) {
            this.dialog.add(AlertDialog, {
                title: _t("Bancontact Payment Error"),
                body: error.data.message,
            });
        }
    },
});

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { markup } from "@odoo/owl";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    // @Override
    async pay() {
        if (this.company.l10n_jo_edi_demo_mode) {
            this.showDemoModeNotification();
        }

        return await super.pay();
    },

    // @Override
    onClickBackButton() {
        this.closeDemoModeNotification();
        return super.onClickBackButton();
    },

    showDemoModeNotification() {
        this.closeDemoModeNotification();

        this._demoModeNotificationClose = this.env.services.notification.add(
            markup(
                _t(`
                    Demo mode is enabled:<br/>
                    a. To synchronise this order with JoFotara, please change the JoFotara State to "To Send" by accessing
                    Orders > Select the Order > Details > Extra Info or by going to Backend > Orders > Select the Order > Extra Info.
                    Subsequently, please uncheck the Demo Mode by going to Accounting > Configuration > Settings > Demo Mode,
                    before trying again by clicking the JoFotara button on the top on the Order.<br/>
                    b. To revert this order, please go to Orders > Select the Order > Refund or create a Return from the backend by
                    going to Orders > Select the Order > Return.
                `)
            ),
            { type: "warning", sticky: true }
        );
    },

    closeDemoModeNotification() {
        this._demoModeNotificationClose?.();
        this._demoModeNotificationClose = null;
    },
});

import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
<<<<<<< 1eb2578bea64387c70200dd34f748a3c033c10eb
import { reactive, Component, onMounted, onWillStart } from "@odoo/owl";
||||||| a220fb71c036c93fa1e75d4d37127e5eda0118f9
import { reactive, Component, onMounted, onWillStart } from "@odoo/owl";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";
=======
import { Component, onMounted, onWillStart } from "@odoo/owl";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";
>>>>>>> a996366805e4ce15bde43c3ea83c14618f518a2a
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
import { useIdleTimer } from "./utils/use_idle_timer";
import useTours from "./hooks/use_tours";
import { init as initDebugFormatters } from "./utils/debug-formatter";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";

/**
 * Chrome is the root component of the PoS App.
 */
export class Chrome extends Component {
    static template = "point_of_sale.Chrome";
    static components = { Transition, MainComponentsContainer, Navbar };
    static props = { disableLoader: Function };
    setup() {
        this.pos = usePos();
        useIdleTimer(this.pos.idleTimeout, (ev) => {
            const stopEventPropagation = ["mousedown", "click", "keypress"];
            if (stopEventPropagation.includes(ev.type)) {
                ev.stopPropagation();
            }
            this.pos.navigateToFirstPage();
            return false;
        });
        if (this.pos.router.state.current === "SaverScreen") {
            this.pos.navigateToFirstPage();
        }

        window.posmodel = this.pos;
        useOwnDebugContext();
        if (this.env.debug) {
            initDebugFormatters();
        }

        if (odoo.use_pos_fake_tours) {
            window.pos_fake_tour = useTours();
        }

        if (this.pos.config.iface_big_scrollbars) {
            const body = document.getElementsByTagName("body")[0];
            body.classList.add("big-scrollbars");
        }

        onWillStart(this.pos._loadFonts);
        onMounted(this.props.disableLoader);
        effect(
            batched((pos) => {
                this.onPosChanges(pos);
            }),
            [this.pos]
        );
    }

    onPosChanges({ selectedOrder }) {
        if (selectedOrder) {
            this.sendOrderToCustomerDisplay(selectedOrder);
        }
    }

    sendOrderToCustomerDisplay(selectedOrder) {
        const adapter = new CustomerDisplayPosAdapter();
        adapter.formatOrderData(selectedOrder);
        adapter.dispatch(this.pos);
    }

    // GETTERS //
    get showCashMoveButton() {
        return Boolean(this.pos.config.cash_control);
    }
}

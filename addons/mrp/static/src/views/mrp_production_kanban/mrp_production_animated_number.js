/** @odoo-module **/

import { AnimatedNumber } from "@web/views/view_components/animated_number";
import { localization as l10n } from "@web/core/l10n/localization";

export class MrpProductionAnimatedNumber extends AnimatedNumber {

    setup() {
        super.setup();
        this.constructor.enableAnimations = false;
    }
    format(value) {
        return new Intl.DurationFormat(l10n.locale, { style: "short", unit: "hours" }).format({ "hours": (value / 60) | 0 });
    }
}

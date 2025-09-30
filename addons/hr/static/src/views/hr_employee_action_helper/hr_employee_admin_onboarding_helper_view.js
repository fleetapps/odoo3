import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { OnboardingHelperBlocks } from "@hr/views/onboarding/onboarding_helper_blocks";

// Similar to `HrEmployeeOnboardingHelper`, but adds `Load sample Data` and `Create Employee` buttons
export class HrEmployeeAdminOnboardingHelper extends Component {
    static template = "hr.EmployeeAdminOnboardingHelper";
    static components = { OnboardingHelperBlocks };
    static props = {};

    setup() {
        super.setup();
        this.orm = useService("orm");
        this._actionService = useService("action");
    }

    async loadDemoData() {
        await this.orm.call("hr.employee", "load_demo_data", []);
        this._actionService.doAction("reload");
    }

    loadNewEmployeeForm() {
        this._actionService.doAction({
            name: _t("Employees"),
            res_model: "hr.employee",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
        });
    }
}

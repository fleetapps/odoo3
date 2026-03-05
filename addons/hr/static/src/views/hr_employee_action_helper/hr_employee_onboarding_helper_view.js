import { Component } from "@odoo/owl";
import { OnboardingHelperBlocks } from "../onboarding/onboarding_helper_blocks";

// Similar to `HrEmployeeAdminOnboardingHelper`, but without the `Load sample Data` and `Create Employee` buttons
export class HrEmployeeOnboardingHelper extends Component {
    static template = "hr.EmployeeOnboardingHelper";
    static components = { OnboardingHelperBlocks };
    static props = {};
}

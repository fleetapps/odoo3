import { ActionHelper } from "@web/views/action_helper";
import { user } from "@web/core/user";
import { onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { HrEmployeeOnboardingHelper } from "./hr_employee_onboarding_helper_view";
import { HrEmployeeAdminOnboardingHelper } from "./hr_employee_admin_onboarding_helper_view";

/**
 * Either:
 * - Hide
 * - Display the onboarding helper
 * - Display the helper defined by the view (props.noContentHelp)
 */
export class HrEmployeeActionHelper extends ActionHelper {
    static template = "hr.EmployeeActionHelper";
    static components = {
        HrEmployeeOnboardingHelper,
        HrEmployeeAdminOnboardingHelper,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.getEmployeesCount = this.env.getEmployeesCount;
        this.state = useState({ hasEmployeeRights: null, helperType: null });
        onWillStart(async () => {
            this.state.hasEmployeeRights = await user.checkAccessRight("hr.employee", "create");
            const isOnboarding = await this.orm.call("hr.employee", "is_onboarding", [
                user.activeCompanies.map((company) => company.id),
            ]);
            this.state.helperType = isOnboarding ? "onboarding" : "default";
        });
    }

    get isOnboardingHelper() {
        return this.state.helperType == "onboarding";
    }

    get showHelper() {
        return this._getState() != "hide";
    }

    get showOnboardingLoadSample() {
        return this._getState() == "showOnboardingLoadSample";
    }

    _getState() {
        return getState(
            this.getEmployeesCount(),
            this.isOnboardingHelper,
            this.state.hasEmployeeRights
        );
    }
}

export function getState(employeesCount, isOnboarding, hasEmployeeRights) {
    if (employeesCount > 0) {
        return "hide";
    }

    if (isOnboarding) {
        if (hasEmployeeRights) {
            return "showOnboardingLoadSample";
        }
        return "showOnboardingMessage";
    }

    return "showDefaultHelper";
}

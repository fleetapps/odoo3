import { test, expect } from "@odoo/hoot";
import { getState } from "@hr/views/hr_employee_action_helper/hr_employee_action_helper";

test("HrEmployeeActionHelper hideHelper", () => {
    let isOnboarding = true;
    let hasEmployeeRights = true;
    const employees = 2;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "hide");

    // Whatever the changed value, as there are employees in the view, it should still hide the helper
    isOnboarding = false;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "hide");

    hasEmployeeRights = false;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "hide");
});

test("HrEmployeeActionHelper onboarding", () => {
    const isOnboarding = true;
    let hasEmployeeRights = true;
    const employees = 0;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "showOnboardingLoadSample");

    hasEmployeeRights = false;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "showOnboardingMessage");
});

test("HrEmployeeActionHelper default helper test", () => {
    const isOnboarding = false;
    let hasEmployeeRights = true;
    const employees = 0;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "showDefaultHelper");

    hasEmployeeRights = false;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "showDefaultHelper");
});

function _testHelperState(isOnboarding, hasEmployeeRights, employeesCount, expectedState) {
    const helperState = getState(employeesCount, isOnboarding, hasEmployeeRights);
    expect(helperState).toBe(expectedState, {
        message:
            `For isOnboarding: ${isOnboarding} - hasEmployeeRights: ${hasEmployeeRights} - employeesNbr: ${employeesCount} ` +
            `=====  Expected '${expectedState}', got '${helperState._state}'.`,
    });
}

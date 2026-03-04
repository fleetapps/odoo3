import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { booleanToggleField, BooleanToggleField } from "@web/views/fields/boolean_toggle/boolean_toggle_field";

export class AccountTaxInclExclToggleField extends BooleanToggleField {
    static template = "account.TaxInclExclToggleField";


}

export const accountTaxInclExclToggleField = {
    ...booleanToggleField,
    component: AccountTaxInclExclToggleField,
    displayName: _t("Tax Included/Excluded Toggle"),
    supportedTypes: ["selection"],
};

registry.category("fields").add("account_tax_incl_excl_toggle", accountTaxInclExclToggleField);
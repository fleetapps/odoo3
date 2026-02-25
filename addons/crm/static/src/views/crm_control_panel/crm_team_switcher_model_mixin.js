import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";

/**
 * Mixin adding a method to handle the CRM team switcher selection into the model search domain.
 */
export const CrmTeamSwitcherModelMixin = (T) => class CrmTeamSwitcherModelMixin extends T {
    _processSearchDomain(params, domain) {
        const selectedCrmTeams = JSON.parse(browser.localStorage.getItem("selectedTeamIds") || "[]");
        if (selectedCrmTeams.length) {
            if (params?.context) {
                params.context.team_switcher_selected_teams = selectedCrmTeams;
            }
            domain = Domain.and([
                domain,
                [['team_id', 'in', selectedCrmTeams]],
            ]).toList({});
        }
        return domain;
    }
};

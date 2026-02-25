import { ControlPanel } from "@web/search/control_panel/control_panel";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";

import { onWillStart } from "@odoo/owl";

export class CrmControlPanel extends ControlPanel {
    static template = "crm.ControlPanel";

    setup() {
        super.setup();
        this.selectedTeamIdsKey = "selectedTeamIds";
        this.state.selectedTeamIds = JSON.parse(browser.localStorage.getItem(this.selectedTeamIdsKey) || "[]");

        onWillStart(async () => {
            this.accessibleTeams = await this.orm.searchRead("crm.team", [], ["id", "name"], { order: "name asc" });
            if (!this.showTeamSwitcher) {
                return;
            }
            // Filter out inaccessible teams from selection
            this.state.selectedTeamIds = this.state.selectedTeamIds.filter((tid) => this.accessibleTeamIds.includes(tid));
            // Retrieve main team (always exists as long as there's at least one accessible team).
            const [currentResUser] = await this.orm.read("res.users", [user.userId], ["sale_team_id"]);
            this.state.mainTeam = {
                id: currentResUser.sale_team_id[0],
                name: currentResUser.sale_team_id[1],
            };
        });
    }

    get accessibleTeamIds() {
        return this.accessibleTeams.map((t) => t.id);
    }

    get showTeamSwitcher() {
        return this.accessibleTeams.length > 1;
    }

    async applyChanges() {
        // Unselecting main team switch it to be the first selected team
        // (alphabetically as "accessibleTeamIds" is ordered by name asc).
        if (!this.isTeamSelected(this.state.mainTeam.id)) {
            await this.setTeamMain(this.accessibleTeamIds.find((id) => this.state.selectedTeamIds.includes(id)));
        }
        // Apply team selection
        browser.localStorage.setItem(this.selectedTeamIdsKey, JSON.stringify(this.state.selectedTeamIds));
        this.env.searchModel.search();
    }

    isTeamMain(teamId) {
        return this.state.mainTeam.id === teamId;
    }

    isTeamSelected(teamId) {
        return this.state.selectedTeamIds.includes(teamId);
    }

    async setTeamMain(teamId) {
        if (this.isTeamMain(teamId)) {
            return;
        }
        await this.orm.write("res.users", [user.userId], {
            "sale_team_id": teamId,
        });
        this.state.mainTeam = this.accessibleTeams.find((team) => team.id === teamId);
        // Main team always selected
        if (!this.isTeamSelected(teamId)) {
            this.toggleTeamSelection(teamId);
        }
    }

    toggleTeamSelection(teamId) {
        if (this.isTeamSelected(teamId)) {
            this.state.selectedTeamIds = this.state.selectedTeamIds.filter((id) => id !== teamId);
        } else {
            this.state.selectedTeamIds.push(teamId);
        }
    }

    /* --------------------------------------------------------
     * Handlers
     * -------------------------------------------------------- */
    async onSetTeamMain(teamId) {
        if (this.isTeamMain(teamId)) {
            return;
        }
        await this.setTeamMain(teamId);
        this.applyChanges();
    }

    onToggleTeamSelection(teamId) {
        // Do not handle unselect if it's the only team selected
        if (this.state.selectedTeamIds.length === 1 && this.isTeamSelected(teamId)) {
            return;
        }
        this.toggleTeamSelection(teamId);
        this.applyChanges();
    }
}

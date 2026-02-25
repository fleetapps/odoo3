import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { groupBy } from "@web/core/utils/arrays";
import { _t } from "../../core/l10n/translation";
import { formatDateTime } from "@web/core/l10n/dates";
import { useLayoutEffect } from "@web/owl2/utils";

const { DateTime } = luxon;

class OfflineSystray extends Component {
    static template = "web.OfflineSystray";
    static props = {};
    static components = { Dropdown, DropdownItem };

    setup() {
        this.offlineService = useService("offline");
        this.actionService = useService("action");
        useLayoutEffect(this.env.redrawNavbar, () => [
            this.offlineService.offline,
            this.offlineService.hasScheduledCalls,
        ]);
    }

    get groupEntries() {
        const items = [];
        for (const { key, value } of Object.values(this.offlineService.scheduledORM)) {
            const item = {
                id: key,
                timeStamp: value.extras.timeStamp,
                actionName: value.extras.actionName,
                displayName: value.extras.displayName,
                clickable: value.extras.viewType === "form",
                error: value.extras.error,
                tooltip: JSON.stringify({
                    timeStamp: formatDateTime(DateTime.fromMillis(value.extras.timeStamp)),
                    changes: Object.entries(value.extras.changes || {}),
                }),
            };
            if (value.method === "web_save") {
                item.status = value.args[0].length ? _t("Edited") : _t("Created");
                item.statusColor = value.args[0].length ? "2" : "10";
            }
            if (value.method === "unlink") {
                item.status = _t("Deleted");
                item.statusColor = "1";
            }
            if (value.method === "action_archive") {
                item.status = _t("Archive");
                item.statusColor = "8";
            }
            if (value.method === "action_unarchive") {
                item.status = _t("Unarchive");
                item.statusColor = "4";
            }
            items.push(item);
        }
        const sections = Object.entries(groupBy(items, (item) => item.actionName || ""));
        sections.forEach(([_name, items]) => {
            items.sort((itemA, itemB) => itemA.timeStamp - itemB.timeStamp);
        });
        return sections;
    }

    get inError() {
        return Object.values(this.offlineService.scheduledORM).find(
            ({ value }) => value.extras.error
        );
    }

    get classNames() {
        return {
            fa: true,
            "fa-chain-broken": !this.inError,
            "fa-exclamation": this.inError,
            o_nav_entry: true,
            "text-danger": true,
        };
    }

    get labelText() {
        if (this.inError) {
            return _t("Sync Issues");
        }
        if (this.offlineService.offline) {
            return _t("Working offline");
        }
        return _t("Syncing");
    }

    async openView(id) {
        const { value } = this.offlineService.scheduledORM[id];
        const resId = value.args[0]?.[0];
        await this.actionService.doAction(value.extras.actionId, {
            viewType: "form",
            props: { offlineId: id, resId },
            clearBreadcrumbs: true,
        });
    }
}

const offlineSystrayItem = {
    Component: OfflineSystray,
};

registry.category("systray").add("offline", offlineSystrayItem, { sequence: 1000 });

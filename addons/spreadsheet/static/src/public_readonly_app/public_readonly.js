<<<<<<< ae6402be874d100f8e4ad1863e8626edf70ce62e
import { Component, markRaw, onWillStart, useChildSubEnv, useState } from "@odoo/owl";
||||||| 0704801e349417a593906f9b718c98569adc153b
import { Component, onWillStart, useChildSubEnv, useState } from "@odoo/owl";
=======
import { Component, onWillStart, useState } from "@odoo/owl";
>>>>>>> de4bbd9f0ca4e0f862add2f73491674ea1627908
import { useService } from "@web/core/utils/hooks";

import { useSpreadsheetNotificationStore } from "@spreadsheet/hooks";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { Spreadsheet, Model } from "@odoo/o-spreadsheet";
import { useSpreadsheetPrint } from "../hooks";
import { _t } from "@web/core/l10n/translation";

spreadsheet.registries.topbarMenuRegistry.addChild("download_public_excel", ["file"], {
    name: _t("Download"),
    execute: (env) => env.downloadExcel(),
    isReadonlyAllowed: true,
    icon: "o-spreadsheet-Icon.DOWNLOAD",
    isVisible: (env) => env.canDownloadExcel?.(),
});

export class PublicReadonlySpreadsheet extends Component {
    static template = "spreadsheet.PublicReadonlySpreadsheet";
    static components = { Spreadsheet };
    static props = {
        dataUrl: String,
        downloadExcelUrl: { type: [String, Boolean], optional: true },
        mode: { type: String, optional: true },
    };

    setup() {
        useSpreadsheetNotificationStore();
        this.http = useService("http");
        this.state = useState({
            isFilterShown: false,
        });
        useSpreadsheetPrint(() => this.model);
        onWillStart(this.createModel.bind(this));
    }

    get showFilterButton() {
        return (
            this.props.mode === "dashboard" &&
            this.globalFilters.length > 0 &&
            !this.state.isFilterShown
        );
    }

    get globalFilters() {
        if (!this.data.globalFilters || this.data.globalFilters.length === 0) {
            return [];
        }
        return this.data.globalFilters.filter((filter) => filter.value !== "");
    }

    async createModel() {
        this.data = await this.http.get(this.props.dataUrl);
        this.model = new Model(
            this.data,
            {
                mode: this.props.mode === "dashboard" ? "dashboard" : "readonly",
            },
            this.data.revisions || []
        );
        markRaw(this.model);
        if (this.env.debug) {
            // eslint-disable-next-line no-import-assign
            spreadsheet.__DEBUG__ = spreadsheet.__DEBUG__ || {};
            spreadsheet.__DEBUG__.model = this.model;
        }
    }

    toggleGlobalFilters() {
        this.state.isFilterShown = !this.state.isFilterShown;
    }
}

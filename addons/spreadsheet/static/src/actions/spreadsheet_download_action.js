import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { createSpreadsheetModel, waitForDataLoaded } from "@spreadsheet/helpers/model";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";

/**
 * @param {import("@web/env").OdooEnv} env
 * @param {object} action
 */
async function downloadSpreadsheet(env, action) {
    const canExport = await user.hasGroup("base.group_allow_export");
    if (!canExport) {
        env.services.notification.add(
            _t("You don't have the rights to export data. Please contact an Administrator."),
            {
                title: _t("Access Error"),
                type: "danger",
            }
        );
        return;
    }
    let { name, data, sources, stateUpdateMessages, xlsxData } = action.params;
    if (!xlsxData) {
        const model = await createSpreadsheetModel({ env, data, revisions: stateUpdateMessages });
        await waitForDataLoaded(model);
<<<<<<< ae6402be874d100f8e4ad1863e8626edf70ce62e
        xlsxData = await model.exportXLSX();
||||||| 0704801e349417a593906f9b718c98569adc153b
        xlsxData = model.exportXLSX();
=======
        sources = model.getters.getLoadedDataSources();
        xlsxData = model.exportXLSX();
>>>>>>> de4bbd9f0ca4e0f862add2f73491674ea1627908
    }
    await download({
        url: "/spreadsheet/xlsx",
        data: {
            zip_name: `${name}.xlsx`,
            files: new Blob([JSON.stringify(xlsxData.files)], {
                type: "application/json",
            }),
            datasources: new Blob([JSON.stringify(sources)], {
                type: "application/json",
            }),
        },
    });
}

registry
    .category("actions")
    .add("action_download_spreadsheet", downloadSpreadsheet, { force: true });

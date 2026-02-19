import { registries } from "@odoo/o-spreadsheet";
import { globalFieldMatchingRegistry } from "../global_filters/helpers";
import { _t } from "@web/core/l10n/translation";
import { navigateToOdooDatasource } from "../chart/odoo_chart/odoo_chart_helpers";
const { urlRegistry } = registries;

const ODOO_DATA_SOURCE_PREFIX = "odoo-data-source://";

function isDataSourceUrl(url) {
    return url.startsWith(ODOO_DATA_SOURCE_PREFIX);
}

function parseDataSourceUrl(url) {
    if (isDataSourceUrl(url)) {
        const separatorIndex = url.indexOf("/", ODOO_DATA_SOURCE_PREFIX.length);
        return [
            url.substring(ODOO_DATA_SOURCE_PREFIX.length, separatorIndex),
            url.substring(separatorIndex + 1),
        ];
    }
    throw new Error(`${url} is not a valid datasource link`);
}
// odoo-data-source://<dataSourceType>/<dataSourceCoreId>

urlRegistry.add("OdooDataSources", {
    sequence: 70,
    title: _t("Data Sources"),
    match(url) {
        return isDataSourceUrl(url);
    },
    createLink: (url, label) => ({
        url,
        label,
        isExternal: false,
        isUrlEditable: false,
    }),
    urlRepresentation(url, getters) {
        const [dsType, dsId] = parseDataSourceUrl(url);
        return globalFieldMatchingRegistry.get(dsType).getDisplayName(getters, dsId);
    },
    open(url, env, newWindow) {
        const [dsType, dsId] = parseDataSourceUrl(url, env, newWindow);
        navigateToOdooDatasource(env, dsType, dsId, newWindow);
        // parse and then "see record as " -> like for cahrt odoo link
    },
    getLinkProposals(env) {
        const proposals = [];
        const getters = env.model.getters;
        // TODORAR factorize
        for (const dataSourceType of globalFieldMatchingRegistry.getKeys()) {
            const el = globalFieldMatchingRegistry.get(dataSourceType);
            for (const dataSourceCoreId of el.getIds(getters)) {
                const tag = el.getTag(getters, dataSourceCoreId);
                const displayName = el.getDisplayName(getters, dataSourceCoreId);
                proposals.push({
                    label: `${tag} - ${displayName}`,
                    url: `${ODOO_DATA_SOURCE_PREFIX}${dataSourceType}/${dataSourceCoreId}`,
                    icon: getDatasourceIconTemplate(dataSourceType),
                    isExternal: false,
                    isUrlEditable: false,
                });
            }
        }
        return proposals;
    },
});

function getDatasourceIconTemplate(dataSourceType) {
    switch (dataSourceType) {
        case "list":
            return "o-spreadsheet-Icon.ODOO_LIST";
        case "pivot":
            return "o-spreadsheet-Icon.PIVOT";
        case "chart":
            return "o-spreadsheet-Icon.INSERT_CHART";
    }
}

import { registries, constants } from "@odoo/o-spreadsheet";
import { navigateTo } from "@spreadsheet/actions/helpers";
import { CommandResult } from "../../o_spreadsheet/cancelled_reason";
import {
    onGeoOdooChartItemClick,
    onOdooChartItemClick,
    onSunburstOdooChartItemClick,
    onTreemapOdooChartItemClick,
    onWaterfallOdooChartItemClick,
} from "./odoo_chart_helpers";

const { chartDataSourceRegistry } = registries;
const { CHART_TYPES } = constants;

// Types not supported by odoo charts (at least for now)
const EXCLUDED_CHART_TYPES = ["scorecard", "gauge", "calendar"];

chartDataSourceRegistry.add("odoo", {
    supportedChartTypes: Array.from(new Set(CHART_TYPES).difference(new Set(EXCLUDED_CHART_TYPES))),
    fromRangeStr: (definition) => definition,
    validate: (definition) => CommandResult.Success,
    transform: (definition) => definition,
    extractData: (definition, getters) => {
        const sheetId = getters.getActiveSheetId();
        const [chartId] = getters.getChartIds(sheetId);
        const { datasets, labels } = getters.getChartDataSource(chartId).getData();
        for (const ds of datasets) {
            if (ds.cumulatedStart) {
                ds.data[0] += ds.cumulatedStart;
            }
        }
        return {
            dataSetsValues: datasets.map((ds, i) => {
                const identifiers = JSON.parse([...ds.identifiers][0]);
                const mainAxis = definition.metaData.groupBy[0];
                const dataSetId = identifiers
                    .slice(1) // first groupBy is the horizontal axis
                    .map((id) => {
                        const [[fieldName, value]] = Object.entries(id);
                        if (Array.isArray(value)) {
                            return `{"${fieldName}":${value[0]}}`; // [id, display_name]
                        }
                        return `{"${fieldName}":${value}}`;
                    })
                    .join(",");
                return {
                    ...ds,
                    data: ds.data.map((d) => ({ value: d })),
                    dataSetId: mainAxis + dataSetId,
                };
            }),
            labelValues: labels.map((l) => ({ value: l })),
        };
    },
    extractHierarchicalData: (definition, getters) => {
        const sheetId = getters.getActiveSheetId();
        const [chartId] = getters.getChartIds(sheetId);
        const { datasets, labels } = getters.getChartDataSource(chartId).getHierarchicalData();
        return {
            dataSetsValues: datasets.map((ds, i) => ({
                ...ds,
                data: ds.data.map((d) => ({ value: d })),
                dataSetId: i.toString(), // FIXME
            })),
            labelValues: labels.map((l) => ({ value: l })),
        };
    },
    onDataSetHover: (chartType, event, items, chart) => {
        if (!event.native) {
            return;
        }
        if (!items.length) {
            event.native.target.style.cursor = "";
            return;
        }
        const item = items[0];
        switch (chartType) {
            case "geo": {
                const data = chart.data.datasets?.[item.datasetIndex]?.data?.[item.index];
                if (
                    typeof data === "object" &&
                    data &&
                    "value" in data &&
                    data.value !== undefined
                ) {
                    event.native.target.style.cursor = "pointer";
                } else {
                    event.native.target.style.cursor = "";
                }
                break;
            }
            default: {
                if (items.length > 0) {
                    event.native.target.style.cursor = "pointer";
                } else {
                    event.native.target.style.cursor = "";
                }
            }
        }
    },
    onDataSetClick: (chartType, chartId, event, items, chartJSChart, getters) => {
        switch (chartType) {
            case "geo":
                return onGeoOdooChartItemClick(getters, chartId)(event, items, chartJSChart);
            case "sunburst":
                return onSunburstOdooChartItemClick(getters, chartId)(event, items, chartJSChart);
            case "treemap":
                return onTreemapOdooChartItemClick(getters, chartId)(event, items, chartJSChart);
            case "waterfall":
                return onWaterfallOdooChartItemClick(getters, chartId)(event, items, chartJSChart);
            default:
                return onOdooChartItemClick(getters, chartId)(event, items, chartJSChart);
        }
    },
    goToDataSet: async (definition, name, dataSet, index, newWindow, getters) => {
        const domain = dataSet.domains[index];
        if (!domain || !name) {
            return;
        }
        await navigateTo(
            getters.getOdooEnv(),
            definition.actionXmlId,
            {
                name,
                type: "ir.actions.act_window",
                res_model: definition.metaData.resModel,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain,
            },
            { viewType: "list", newWindow }
        );
    },
    adaptRanges: (definition) => definition,
    getDefinition: (dataSource) => dataSource,
    duplicateInDuplicatedSheet: (dataSource) => dataSource,
    getContextCreation: () => ({}),
    getHierarchicalContextCreation: () => ({}),
    toExcelDataSets: () => ({ dataSets: [], labelRange: "" }),
});

import { registries} from "@odoo/o-spreadsheet";
import "./odoo_chart_datasource"; // ensure the data source is registered.

const { chartTypeRegistry, chartDataSourceRegistry } = registries;

// Legacy compatibility: before datasetStyles was added to the definition, identified with an id,
// styles were stored in an array in the same order as datasets. This code migrates from the old format to the new one.

const odooTypes = chartDataSourceRegistry.get("odoo").supportedChartTypes;

const hierarchical = ["sunburst", "treemap"];

for (const chartTypeBuilder of chartTypeRegistry.getAll()) {
    const getRuntime = chartTypeBuilder.getRuntime;
    chartTypeBuilder.getRuntime = (getters, definition, dataSource, sheetId, eventHandlers) => {
        if (!odooTypes.includes(definition.type) || (definition.datasetStyles && !definition.dataSets)) {
            return getRuntime(getters, definition, dataSource, sheetId, eventHandlers);
        }
        const data = hierarchical.includes(definition.type) ? dataSource.extractData() : dataSource.extractHierarchicalData();
        const datasetStyles = {};
        for (let i = 0; i < data.dataSetsValues.length; i++) {
            const ds = data.dataSetsValues[i];
            const style = definition.dataSets[i];
            datasetStyles[ds.dataSetId] = style;
        }
        definition.datasetStyles = datasetStyles;
        delete definition.dataSets;
        return getRuntime(getters, definition, dataSource, sheetId, eventHandlers);
    };
}
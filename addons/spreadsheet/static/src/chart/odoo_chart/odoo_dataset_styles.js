import { registries } from "@odoo/o-spreadsheet";

const { chartTypeRegistry } = registries;

// Legacy compatibility: before datasetStyles was added to the definition, identified with an id,
// styles were stored in an array in the same order as datasets. This code migrates from the old format to the new one.

const hierarchical = ["sunburst", "treemap"];

for (const chartTypeBuilder of chartTypeRegistry.getAll()) {
    const getRuntime = chartTypeBuilder.getRuntime;
    chartTypeBuilder.getRuntime = (
        getters,
        definition,
        dataSourceExtractor,
        sheetId,
        eventHandlers
    ) => {
        console.log(definition.type);
        const isOdoo = definition.dataSource?.type === "odoo";
        if (!isOdoo || !definition.dataSets?.length) {
            return getRuntime(getters, definition, dataSourceExtractor, sheetId, eventHandlers);
        }
        const data = hierarchical.includes(definition.type)
            ? dataSourceExtractor.extractData()
            : dataSourceExtractor.extractHierarchicalData();
        const datasetStyles = {};
        for (let i = 0; i < data.dataSetsValues.length; i++) {
            const ds = data.dataSetsValues[i];
            const style = definition.dataSets[i];
            datasetStyles[ds.dataSetId] = style;
        }
        definition.datasetStyles = datasetStyles;
        delete definition.dataSets;
        return getRuntime(getters, definition, dataSourceExtractor, sheetId, eventHandlers);
    };
}

import { useMatrixConfigurator } from "@product_matrix/js/matrix_configurator_hook";
import { SaleOrderLineProductField, saleOrderLineProductField } from "@sale/js/sale_product_field";
import { patch } from "@web/core/utils/patch";

patch(SaleOrderLineProductField.prototype, {
    setup() {
        super.setup(...arguments);
        this.matrixConfigurator = useMatrixConfigurator();
    },

    async _openGridConfigurator(edit=false) {
        return this.matrixConfigurator.open(this.props.record, edit);
    },

    async _openProductConfigurator(params = {}) {
        const isEdit = typeof params === 'object' ? params.edit : params;

        if (isEdit && this.props.record.data.product_add_mode === 'matrix') {
            this._openGridConfigurator(true);
        } else {
            const result = await this._getPreloadedConfigData();
            const superParams = typeof params === 'object' ? { ...params } : { edit: params };
            superParams.preloadedData = result?.preloaded_config_data;
            return super._openProductConfigurator(superParams);
        }
    },
});

Object.assign(saleOrderLineProductField, {
    fieldDependencies: [
        ...saleOrderLineProductField.fieldDependencies,
        { name: "product_add_mode", type: "selection"},
    ],
});

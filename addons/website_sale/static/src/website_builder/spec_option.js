import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { reactive, useState } from "@web/owl2/utils";
import { onWillStart } from "@odoo/owl";

export class SpecificationsOption extends BaseOptionComponent {
    static template = "website_sale.SpecificationsOption";
    static selector = "#product_full_spec .o_wsale_specss";
    static editableOnly = false;
    static reloadTarget = true;
    static dependencies = ['specificationsOption']

    setup() {
        super.setup();
        const {loadSpecs} = this.dependencies.specificationsOption;

        this.state = useState({
            fields: [],
            categories: [],
            showField: false,
        });

        onWillStart(async () => {
            const data = await loadSpecs();
            this.state.fields = data.fields;
            this.state.categories = data.categories;
        });
    }

}

class SpecificationsPlugin extends Plugin {
    static id = "specificationsOption";
    static shared = ["loadSpecs"];
    resources = {
        builder_options: SpecificationsOption,
    };

    async loadSpecs() {
        if(!this.data) {
            const fields = await this.services.orm.searchRead(
                'ir.model.fields',
                [
                    ['model', '=', 'product.template'],
                    ['ttype', 'in', ['char', 'binary']]
                ],
                ['id', 'name', 'field_description']
            );
            const categories = await this.services.orm.searchRead(
                'product.attribute.category',
                [],
                ['id', 'name']
            )
            this.data = {
                fields,
                categories,
            };
        }

        return this.data;
    }
}

registry
    .category("website-plugins")
    .add(SpecificationsPlugin.id, SpecificationsPlugin);

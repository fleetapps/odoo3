import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { standardFieldProps } from "../standard_field_props";
import { getFontAwesomeIcons } from "@web/views/utils"

export class FontAwesomeIconField extends Component {
    static template = "web.FontAwesomeIconField";
    static components = { SelectMenu };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.ICONS = getFontAwesomeIcons();
    }

    get choices() {
        return this.ICONS.map(icon => ({
            value: icon.className,
            label: icon.searchTerms.join(" "),
        }));
    }

    get iconValue() {
        return this.props.record.data[this.props.name] || "";
    }

    getIconTooltip(value) {
        const icon = this.ICONS.find(i => i.className === value);
        return icon?.tooltip || "";
    }

    onSelect = (value) => {
        this.props.record.update({
            [this.props.name]: value,
        });
    }
}

registry.category("fields").add("fa_icon", {
    component: FontAwesomeIconField,
    supportedTypes: ["char"],
});

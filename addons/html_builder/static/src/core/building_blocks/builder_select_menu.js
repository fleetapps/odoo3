import { Component, onMounted, useState } from "@odoo/owl";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { shallowEqual } from "@web/core/utils/objects";
import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import {
    basicContainerBuilderComponentProps,
    useInputBuilderComponent,
} from "@html_builder/core/utils";

export class BuilderSelectMenu extends Component {
    static template = "html_builder.BuilderSelectMenu";
    static components = { BuilderComponent, SelectMenu };

    static defaultProps = {
        multiSelect: false,
    };

    static props = {
        ...basicContainerBuilderComponentProps,
        choices: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    value: true,
                    label: { type: String },
                },
            },
        },
        multiSelect: { type: Boolean, optional: true },
    };

    setup() {
        this.uiState = useState({
            value: this.props.multiSelect ? [] : null,
        });

        const { state, commit } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.props.multiSelect ? [] : null,
            parseDisplayValue: (displayValue) => JSON.stringify(displayValue),
            formatRawValue: this.formatRawValue.bind(this),
        });

        this.domState = state;
        this.commit = commit;

        onMounted(() => {
            const value = this.domState.value;
            const hasValidValue = Array.isArray(value)
                ? value.length > 0
                : value !== null;
            if (hasValidValue) {
                this.uiState.value = this._rehydrateFromDomState();
            }
        });
    }
    _rehydrateFromDomState() {
        const parsed = this.formatRawValue(this.domState.value);

        if (this.props.multiSelect) {
            return parsed
                .map((raw) => {
                    const match = this.props.choices.find((choice) =>
                        shallowEqual(choice.value, raw),
                    );
                    return match ? match.value : null;
                })
                .filter(Boolean);
        }

        const match = this.props.choices.find((choice) =>
            shallowEqual(choice.value, parsed),
        );
        return match ? match.value : null;
    }
    onSelect(value) {
        this.uiState.value = value;
        this.commit(value);
    }
    formatRawValue(rawValue) {
        return JSON.parse(rawValue);
    }
}

import { LinkPopover } from "@html_editor/main/link/link_popover";

export class WebsiteLinkPopover extends LinkPopover {
    setup() {
        super.setup();
        const currentRelValues = this.props.linkElement.rel.split(" ");
        const currentTargetValue = this.props.linkElement.getAttribute("target");
        this.state.advancedAttributeOptions = Object.fromEntries(
            this.props.advancedAttributeOptions.map((option) => [
                option.label,
                {
                    ...option,
                    isChecked:
                        option.attribute === "rel"
                            ? currentRelValues.includes(option.value)
                            : option.attribute === "target"
                            ? currentTargetValue === option.value
                            : false,
                },
            ])
        );
    }

    toggleAdvancedOptions() {
        this.state.showAdvancedOptions = !this.state.showAdvancedOptions;
    }

    toggleAdvancedAttr(attr) {
        const option = this.state.advancedAttributeOptions[attr];
        option.isChecked = !option.isChecked;
        if (option.attribute === "target" && !option.isChecked) {
            this.state.advancedAttributeOptions.noopener.isChecked = false;
        }
    }

    prepareParams() {
        const relOptions = Object.values(this.state.advancedAttributeOptions);
        const base = super.prepareParams();
        const rel =
            relOptions
                .filter((opt) => opt.attribute === "rel" && opt.isChecked)
                .map((opt) => opt.value)
                .join(" ") || null;
        const target =
            relOptions.find((opt) => opt.attribute === "target" && opt.isChecked)?.value || null;
        return {
            ...base,
            attributes: {
                ...base.attributes,
                rel,
                target,
            },
        };
    }
}

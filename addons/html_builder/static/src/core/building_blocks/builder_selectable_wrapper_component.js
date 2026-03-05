import { useActionInfo, useSelectableLtrRtlComponent } from "@html_builder/core/utils";
import { Component } from "@odoo/owl";
import { useState } from "@web/owl2/utils";

export class BuilderSelectableWrapperComponent extends Component {
    static template = "";
    static props = {
        ltrRtlSharedId: { type: String, optional: true },
        isLabelLinkedToContent: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        "*": { optional: true },
    };

    setup() {
        const info = useActionInfo({ stringify: false });
        this.itemPropsState = useState({
            className: this.props.className,
            label: this.props.label,
            title: this.props.title,
            slots: this.props.slots,
            actionParam: info.actionParam,
            actionValue: info.actionValue,
            classAction: info.classAction,
            styleAction: info.styleAction,
            styleActionValue: info.styleActionValue,
            attributeAction: info.attributeAction,
            attributeActionValue: info.attributeActionValue,
            dataAttributeAction: info.dataAttributeAction,
            dataAttributeActionValue: info.dataAttributeActionValue,
        });

        if (this.props.ltrRtlSharedId && !this.env.ignoreBuilderItem) {
            useSelectableLtrRtlComponent({
                ltrRtlSharedId: this.props.ltrRtlSharedId,
                isLabelLinkedToContent: this.props.isLabelLinkedToContent,
                getItemState: () => this.itemPropsState,
            });
        }
    }

    get itemProps() {
        const forwardedProps = { ...this.props };
        delete forwardedProps.ltrRtlSharedId;
        delete forwardedProps.isLabelLinkedToContent;
        return { ...forwardedProps, ...this.itemPropsState };
    }
}

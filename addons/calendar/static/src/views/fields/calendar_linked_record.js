import { ModelSelector } from "@web/core/model_selector/model_selector";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ReferenceField } from "@web/views/fields/reference/reference_field";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

export class CalendarLinkedRecord extends ReferenceField {
    static template = "calendar.CalendarLinkedRecord";
    static props = { ...ReferenceField.props };
    static components = { ModelSelector };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.action = useService("action");
    }

    get availableModels() {
        return this.selection.map((item) => item[0]);
    }

    onModelSelected(model) {
        const resModel = model.technical;
        if (resModel) {
            this.dialog.add(SelectCreateDialog, {
                resModel: resModel,
                title: "Select a Record To Link",
                noCreate: true,
                multiSelect: false,
                onSelected: async (resIds) => {
                    const resId = resIds[0];
                    if (resId) {
                        await this.props.record.update({
                            [this.props.name]: {
                                resModel: resModel,
                                resId: resId,
                            },
                        });
                    }
                },
            });
        }
    }

    openRecord() {
        const value = this.getValue();
        if (!value?.resId || !value?.resModel) {
            return;
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: value.resModel,
            res_id: value.resId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    clearRecord() {
        this.props.record.update({ [this.props.name]: false });
    }
}

export const calendarLinkedRecord = {
    component: CalendarLinkedRecord,
    displayName: "Linked Record Selector",
    supportedTypes: ["reference"],
};

registry.category("fields").add("calendar_linked_record", calendarLinkedRecord);

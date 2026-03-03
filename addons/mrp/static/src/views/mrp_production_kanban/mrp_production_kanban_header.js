/** @odoo-module **/

import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { MrpProductionColumnProgress } from "./mrp_production_column_progress";

export class MrpProductionKanbanHeader extends KanbanHeader {
    static components = {
        ...KanbanHeader.components,
        ColumnProgress: MrpProductionColumnProgress,
    };

    get groupAggregate() {
        let value = 0;
        for (let record of this.props.group.list.records) {
            value += record.data["remaining_time"];
        }
        return { value };
    }
}

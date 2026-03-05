import { patch } from "@web/core/utils/patch";
import { SMLX2ManyField } from "@stock/fields/stock_move_line_x2_many_field";

patch(SMLX2ManyField.prototype, {
    async onAdd(params) {
        params.context = {
            ...params.context,
            use_expiration_date: this.props.record.data.use_expiration_date,
        };
        return super.onAdd(params);
    },
});

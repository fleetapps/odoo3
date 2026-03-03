import { HrEmployee } from "@hr/../tests/mock_server/mock_models/hr_employee";

import { patch } from "@web/core/utils/patch";

patch(HrEmployee.prototype, {
    _get_store_avatar_card_fields() {
        return [...super._get_store_avatar_card_fields(), "leave_date_to"];
    },
});

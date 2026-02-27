import { useState } from "@web/owl2/utils";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart } from "@odoo/owl";

export class AttendanceActionHelper extends Component {
    static template = "hr_attendance.AttendanceActionHelper";
    static props = ["noContentHelp"];
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            hasDemoData: false,
        });
        onWillStart(async () => {
            const isHrUser = await user.hasGroup("hr.group_hr_user");
            const hasAttendanceRight = await user.hasGroup("hr_attendance.group_hr_attendance_user");
            
            let hasDemoData = false;
            if (this.hasAttendanceRight && this.isHrUser){
                hasDemoData = await this.orm.call("hr.attendance", "has_demo_data", []);
            }

            if (!this.isDestroyed) {
                this.isHrUser = isHrUser;
                this.hasAttendanceRight = hasAttendanceRight;
                this.state.hasDemoData = hasDemoData;
            }
        });
    }

    loadAttendanceScenario() {
        this.actionService.doAction("hr_attendance.action_load_demo_data");
    }

    LoadTryKiosk() {
        this.actionService.doAction("hr_attendance.action_try_kiosk");
    }
};

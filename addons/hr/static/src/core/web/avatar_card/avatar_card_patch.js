import { allowedModels, AvatarCard } from "@mail/discuss/core/web/avatar_card/avatar_card";

import { TagsList } from "@web/core/tags_list/tags_list";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

// Adding TagsList component allows display tag lists on the resource/employee avatar card
// This is used by multiple modules depending on hr (planning for roles and hr_skills for skills)
Object.assign(AvatarCard.components, { TagsList });

allowedModels.push("hr.employee", "hr.employee.public");

/** @type {AvatarCard} */
const avatarCardPatch = {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },
    /** @override */
    get displayAvatar() {
        return super.displayAvatar || Boolean(this.employee);
    },
    /** @override */
    get email() {
        return this.employee?.work_email || super.email;
    },
    get employee() {
        switch (this.props.model) {
            case "hr.employee":
                return this.store["hr.employee"].get(this.props.id);
            case "hr.employee.public":
                return this.publicEmployee?.employee_id;
            case "resource.resource":
                return this.resource?.employee_id;
        }
        return this.partner?.employee_id;
    },
    /** @override */
    get name() {
        return this.employee?.name;
    },
    /** @override */
    get phone() {
        return this.employee?.work_phone || super.phone;
    },
    get publicEmployee() {
        if (this.props.model === "hr.employee.public") {
            return this.store["hr.employee.public"].get(this.props.id);
        }
        return undefined;
    },
    /** @override */
    get resource() {
        return (
            super.resource ||
            (this.props.model !== "resource.resource" ? this.employee?.resource_id : undefined)
        );
    },
    /** @override */
    get showViewProfileBtn() {
        return super.showViewProfileBtn || Boolean(this.employee);
    },
    /** @override */
    get user() {
        return super.user || this.employee?.user_id;
    },
    /** @override */
    get userInfoTemplate() {
        if (this.employee) {
            return "hr.avatarCardUserInfos";
        }
        return super.userInfoTemplate;
    },
    /** @override */
    async getProfileAction() {
        if (!this.employee) {
            return super.getProfileAction(...arguments);
        }
        return this.orm.call("hr.employee", "get_formview_action", [this.employee.id]);
    },
};
export const unpatchAvatarCard = patch(AvatarCard.prototype, avatarCardPatch);

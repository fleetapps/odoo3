import { AvatarCard } from "@mail/discuss/core/web/avatar_card/avatar_card";

import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { patch } from "@web/core/utils/patch";

Object.assign(AvatarCard.components, { BadgeTag });

/** @type {AvatarCard} */
export const avatarCardPatch = {
    /** @override */
    get hasFooter() {
        return this.employee?.employee_skill_ids?.length > 0 || super.hasFooter;
    },
    get skillTags() {
        return this.employee?.employee_skill_ids.map(({ id, display_name, color }) => ({
            id,
            text: display_name,
            color,
        }));
    },
};
export const unpatchAvatarCard = patch(AvatarCard.prototype, avatarCardPatch);

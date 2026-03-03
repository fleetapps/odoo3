import { allowedModels, AvatarCard } from "@mail/discuss/core/web/avatar_card/avatar_card";
import { patch } from "@web/core/utils/patch";

allowedModels.push("resource.resource");

/** @type {AvatarCard} */
const avatarCardPatch = {
    /** @override */
    get displayAvatar() {
        if (this.props.model === "resource.resource") {
            return Boolean(this.resource && this.resource.resource_type !== "material");
        }
        return super.displayAvatar;
    },
    /** @override */
    get name() {
        return this.resource?.name || super.name;
    },
    /** @override */
    get openChatModel() {
        if (this.props.model === "resource.resource") {
            return "res.users";
        }
        return super.openChatModel;
    },
    /** @override */
    get openChatId() {
        if (this.props.model === "resource.resource") {
            return this.user?.id;
        }
        return super.openChatId;
    },
    get resource() {
        if (this.props.model === "resource.resource") {
            return this.store["resource.resource"].get(this.props.id);
        }
        return undefined;
    },
    /** @override */
    get user() {
        return this.resource?.user_id || super.user;
    },
};
patch(AvatarCard.prototype, avatarCardPatch);

import { defineModels } from "@web/../tests/web_test_helpers";
import { hrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { websiteLivechatModels } from "@website_livechat/../tests/website_livechat_test_helpers";
import { DiscussChannelMember } from "@im_livechat/../tests/mock_server/mock_models/discuss_channel_member";
import { DiscussChannel } from "@im_livechat/../tests/mock_server/mock_models/discuss_channel";

export function defineTestDiscussFullModels() {
    return defineModels(testDiscussFullModels);
}

export const testDiscussFullModels = {
    ...websiteLivechatModels,
    ...hrHolidaysModels,
    // reimport the im_livechat ones
    DiscussChannelMember,
    DiscussChannel,
};

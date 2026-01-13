import { useDomState } from "@html_builder/core/utils";
import { ImageAndFaOption } from "@html_builder/plugins/image/image_and_fa_option";
import { socialMediaElementsSelector } from "@html_builder/plugins/image/replace_media_option";
import { isInsideSocialSnippet } from "@website/builder/plugins/utils";

export class WebsiteImageAndFaOption extends ImageAndFaOption {
    static template = "website.ImageAndFaOption";
    static exclude = `[data-oe-type='image'] > img, [data-oe-xpath], ${socialMediaElementsSelector}`;

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const isInSocialSnippet = isInsideSocialSnippet(editingElement);
            return {
                isImage: editingElement.tagName === "IMG",
                showBorder: !isInSocialSnippet,
            };
        });
    }
}

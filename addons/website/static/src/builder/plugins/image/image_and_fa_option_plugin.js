import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { IMAGE_LINK_ALIGN_CLASSES } from "@html_builder/plugins/image/image_tool_option_plugin";
import { ALIGNMENT_STYLE_PADDING } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { WebsiteImageAndFaOption } from "@website/builder/plugins/image/image_and_fa_option";

class WebsiteImageAndFaOptionPlugin extends Plugin {
    static id = "website.ImageAndFaOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(ALIGNMENT_STYLE_PADDING, WebsiteImageAndFaOption)],
        builder_actions: {
            ImageAlignClassAction,
        },
    };
}

export class ImageAlignClassAction extends ClassAction {
    static id = "imageAlignClassAction";
    apply(context) {
        super.apply(context);
        this.syncLinkAlignment(context.editingElement);
    }
    syncLinkAlignment(editingElement) {
        const linkEl = editingElement.parentElement;
        if (
            !linkEl ||
            linkEl.tagName !== "A" ||
            linkEl.firstElementChild !== editingElement ||
            linkEl.childElementCount !== 1 ||
            linkEl.textContent.replace(/\u200B/g, "").trim() // ignore ZWSP
        ) {
            return;
        }
        // Mirror image alignment classes on the wrapping <a> (only when it
        // wraps just this image) so flex layouts stay consistent.
        const alignClasses = IMAGE_LINK_ALIGN_CLASSES.filter((cls) =>
            editingElement.classList.contains(cls)
        );
        for (const className of IMAGE_LINK_ALIGN_CLASSES) {
            linkEl.classList.toggle(className, alignClasses.includes(className));
        }
    }
}

registry
    .category("builder-plugins")
    .add(WebsiteImageAndFaOptionPlugin.id, WebsiteImageAndFaOptionPlugin);

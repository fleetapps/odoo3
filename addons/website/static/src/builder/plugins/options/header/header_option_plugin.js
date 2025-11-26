import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { HeaderTopOptions } from "./header_top_options";

export class HeaderOptionPlugin extends Plugin {
    static id = "headerOption";
    static dependencies = ["customizeWebsite", "menuDataPlugin"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_header_middle_buttons: [
            {
                Component: HeaderTopOptions,
                editableOnly: false,
                selector: "#wrapwrap > header",
                props: {
                    openEditMenu: () => this.dependencies.menuDataPlugin.openEditMenu(),
                },
            },
        ],
        // we consider the container of Contact Us allows inline element at root
        // to avoid wrapping the button in a <p> or <div>, which would remove
        // this button if it's empty
        are_inlines_allowed_at_root_predicates: (node) =>
            node.matches("#o_main_nav .oe_structure_solo .oe_unremovable [contenteditable='true']"),
    };
}

registry.category("website-plugins").add(HeaderOptionPlugin.id, HeaderOptionPlugin);

import { Image } from "@html_builder/core/img";
import { handleMatrixKeyNavigation } from "@html_builder/utils/backend_utils";
import { Component } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

export class Snippet extends Component {
    static template = "html_builder.Snippet";
    static components = { Image };
    static props = {
        snippetModel: { type: Object },
        snippet: { type: Object },
        onClickHandler: { type: Function },
        disabledTooltip: { type: String },
    };

    get snippet() {
        return this.props.snippet;
    }

    onInstallableHover(ev) {
        if (this.snippet.isInstallable) {
            ev.currentTarget
                .querySelector(".o_install_btn")
                .classList.toggle("visually-hidden-focusable", ev.type !== "mouseover");
        }
    }

    onBtnKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "enter" || hotkey === "space") {
            this.props.onClickHandler(ev);
        }
        handleMatrixKeyNavigation(ev, {
            containerEl: ev.currentTarget.closest(".o_snippets_container_body"),
            focusedItemSelector: ".o_snippet",
            focusableElSelector: "button",
        });
    }

    onClickInstall() {
        this.props.snippetModel.installSnippetModule(
            this.props.snippet,
            this.env.editor.config.installSnippetModule
        );
    }
}

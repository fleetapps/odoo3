import { SNIPPET_SPECIFIC, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

/** @typedef {import("plugins").LazyTranslatedString} LazyTranslatedString */

/**
 * @typedef {{
 *      value: string;
 *      label: LazyTranslatedString;
 *      pageSelector: string | null;
 * }} popup_show_on_options
 *
 * Register "Show on" options for the popup snippet.
 * `value` is the internal identifier used in `data-show-on` attribute.
 * `label` is the human-readable label shown in the dropdown.
 * `pageSelector` is a CSS selector matched against the current page at
 * runtime to decide whether to show the popup. Use `null` for options
 * that should show on all pages (e.g. "All pages", "This page").
 *
 * Example:
 *
 *      resources: {
 *          popup_show_on_options: withSequence(30, {
 *              value: "allProducts",
 *              label: _t("All Products"),
 *              pageSelector: ".o_wsale_product_page",
 *          }),
 *      };
 */

export const POPUP = SNIPPET_SPECIFIC;
export const COOKIES_BAR = SNIPPET_SPECIFIC_END;

const SHARED_BLOCKS_SELECTOR = "#o_shared_blocks";
const SHOW_ON_CURRENT_PAGE = "currentPage";
const SHOW_ON_ALL_PAGES = "allPages";

export class PopupOption extends BaseOptionComponent {
    static template = "website.PopupOption";
    static selector = ".s_popup";
    static exclude = "#website_cookies_bar";
    static applyTo = ".modal";

    setup() {
        super.setup();
        this.showOnOptions = this.getResource("popup_show_on_options");
    }
}

export class PopupCookiesOption extends BaseOptionComponent {
    static template = "website.PopupCookiesOption";
    static selector = ".s_popup#website_cookies_bar";
    static applyTo = ".modal";
}

function getPopupContainerFromSelectors(editable, selectors) {
    for (const selector of selectors) {
        const containerEl = editable.querySelector(selector);
        if (containerEl) {
            return containerEl;
        }
    }
    return null;
}

class PopupOptionPlugin extends Plugin {
    static id = "PopupOption";
    static dependencies = ["anchor", "visibility", "history", "popupVisibilityPlugin"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            withSequence(POPUP, PopupOption),
            withSequence(COOKIES_BAR, PopupCookiesOption),
        ],
        dropzone_selector: {
            selector: ".s_popup",
            exclude: "#website_cookies_bar",
            excludeAncestor: ".s_popup, .s_table_of_content, .s_tabs, .s_tabs_images",
            dropIn: ":not(p).oe_structure:not(.oe_structure_solo):not([data-snippet] *), :not(.o_mega_menu):not(p)[data-oe-type=html]:not([data-snippet] *)",
        },
        builder_actions: {
            // Moves the snippet in #o_shared_blocks to be common to all pages
            // or inside the first editable oe_structure in the main to be on
            // current page only.
            MoveBlockAction,
            SetBackdropAction,
            CopyAnchorAction,
            SetPopupDelayAction,
        },
        is_node_empty_predicates: (el) => {
            if (!el.matches?.(".s_popup")) {
                return;
            }
            const popupModalChildrenEls = [...(el.querySelector(".modal-content")?.children ?? [])];
            return popupModalChildrenEls.every((child) => child.matches(".s_popup_close"));
        },
        on_cloned_handlers: this.onCloned.bind(this),
        on_snippet_dropped_handlers: withSequence(0, this.onSnippetDropped.bind(this)),
        // TODO remove when popup dragging from the page is disabled.
        on_element_dropped_handlers: withSequence(0, this.onElementDropped.bind(this)),
        on_will_remove_handlers: this.onWillRemove.bind(this),
        no_parent_containers: ".s_popup",
        popup_container_selectors: withSequence(10, "main .oe_structure.o_savable"),
        popup_show_on_options: [
            withSequence(10, {
                value: SHOW_ON_CURRENT_PAGE,
                label: _t("This page"),
                pageSelector: null,
            }),
            withSequence(20, {
                value: SHOW_ON_ALL_PAGES,
                label: _t("All pages"),
                pageSelector: null,
            }),
        ],
    };

    onCloned({ cloneEl }) {
        if (cloneEl.matches(".s_popup")) {
            this.assignUniqueID(cloneEl);
        }
    }

    onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_popup")) {
            this.relocatePopup(snippetEl);
            snippetEl.dataset.showOn = SHOW_ON_CURRENT_PAGE;
            this.assignUniqueID(snippetEl);
            this.dependencies.history.addCustomMutation({
                apply: () => {
                    this.dependencies.visibility.toggleTargetVisibility(snippetEl, true);
                },
                revert: () => {
                    this.dependencies.visibility.toggleTargetVisibility(snippetEl, false);
                },
            });
        }
    }

    onWillRemove(el) {
        this.dependencies.visibility.toggleTargetVisibility(el, false);
        this.dependencies.history.addCustomMutation({
            apply: () => {
                this.dependencies.visibility.toggleTargetVisibility(el, false);
            },
            revert: () => {
                this.dependencies.visibility.toggleTargetVisibility(el, true);
            },
        });
    }

    assignUniqueID(editingElement) {
        editingElement.closest(".s_popup").id = `sPopup${Date.now()}`;
    }

    onElementDropped({ droppedEl }) {
        if (droppedEl.matches(".s_popup")) {
            this.relocatePopup(droppedEl);
        }
    }

    relocatePopup(editingElement) {
        const popupEl = editingElement.closest(".s_popup");
        if (popupEl.closest(SHARED_BLOCKS_SELECTOR)) {
            return;
        }
        const containerEl = getPopupContainerFromSelectors(
            this.editable,
            this.getResource("popup_container_selectors")
        );
        if (containerEl) {
            containerEl.insertAdjacentElement("afterbegin", popupEl);
        }
    }
}

// Moves the snippet in #o_shared_blocks to be common to all pages
// or inside the first editable oe_structure in the main to be on
// current page only.
export class MoveBlockAction extends BuilderAction {
    static id = "moveBlock";
    isApplied({ editingElement, value }) {
        const popupEl = editingElement.closest(".s_popup");
        const showOn = popupEl?.dataset.showOn;
        if (showOn) {
            return showOn === value;
        }
        // Backward compat: no data-show-on attr yet, infer from DOM location.
        return popupEl?.closest(SHARED_BLOCKS_SELECTOR)
            ? value === SHOW_ON_ALL_PAGES
            : value === SHOW_ON_CURRENT_PAGE;
    }
    apply({ editingElement, value }) {
        const popupEl = editingElement.closest(".s_popup");
        popupEl.dataset.showOn = value;
        if (value === SHOW_ON_CURRENT_PAGE) {
            const whereEl = getPopupContainerFromSelectors(
                this.editable,
                this.getResource("popup_container_selectors")
            );
            if (whereEl) {
                whereEl.insertAdjacentElement("afterbegin", popupEl);
            }
        } else {
            const sharedBlocksEl = this.editable.querySelector(SHARED_BLOCKS_SELECTOR);
            if (sharedBlocksEl) {
                sharedBlocksEl.insertAdjacentElement("afterbegin", popupEl);
            }
        }
        // Set or clear the page-type filter selector. The resource entry for
        // "currentPage" and "allPages" declares pageSelector: null, so both
        // are handled uniformly here — no special-casing per value needed.
        const option = this.getResource("popup_show_on_options").find((opt) => opt.value === value);
        if (option?.pageSelector) {
            popupEl.dataset.showOnSelector = option.pageSelector;
        } else {
            delete popupEl.dataset.showOnSelector;
        }
    }
}
export class SetBackdropAction extends BuilderAction {
    static id = "setBackdrop";
    isApplied({ editingElement }) {
        const hasBackdropColor = !!editingElement.style.getPropertyValue("background-color").trim();
        const hasNoBackdropClass = editingElement.classList.contains("s_popup_no_backdrop");
        return hasBackdropColor && !hasNoBackdropClass;
    }
    apply({ editingElement }) {
        editingElement.classList.remove("s_popup_no_backdrop");
        editingElement.style.setProperty("background-color", "var(--black-50)", "important");
    }
    clean({ editingElement }) {
        editingElement.classList.add("s_popup_no_backdrop");
        editingElement.style.removeProperty("background-color");
    }
}
export class CopyAnchorAction extends BuilderAction {
    static id = "copyAnchor";
    static dependencies = ["anchor"];
    apply({ editingElement }) {
        this.dependencies.anchor.createOrEditAnchorLink(editingElement);
    }
}
export class SetPopupDelayAction extends BuilderAction {
    static id = "setPopupDelay";
    apply({ editingElement, value }) {
        editingElement.dataset.showAfter = value * 1000;
    }
    getValue({ editingElement }) {
        return editingElement.dataset.showAfter / 1000;
    }
}

registry.category("website-plugins").add(PopupOptionPlugin.id, PopupOptionPlugin);

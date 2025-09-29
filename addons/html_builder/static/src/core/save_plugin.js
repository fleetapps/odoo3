import { escapeTextNodes } from "@html_builder/utils/escaping";
import { Plugin } from "@html_editor/plugin";

/**
 * @typedef { Object } SaveShared
 * @property { SavePlugin['save'] } save
 * @property { SavePlugin['prepareElementForSave'] } prepareElementForSave
 */

/**
 * @typedef {((el?: HTMLElement) => void)[]} on_saved_handlers
 * @typedef {((el?: HTMLElement, groupedEls?: Object.<string, HTMLElement[]>) => Promise<void>)[]} on_will_save_handlers
 * Called before the save process.
 *
 * @typedef {(() => Promise<boolean>)[]} on_ready_to_save_document_handlers
 * Called concurrently as part of the save process.
 */

export class SavePlugin extends Plugin {
    static id = "savePlugin";
    static shared = ["save", "prepareElementForSave"];
    static dependencies = ["history"];

    async save({ shouldSkipAfterSaveHandlers = async () => true } = {}) {
        let skipAfterSaveHandlers;
        try {
            await Promise.all(this.trigger("on_will_save_handlers"));
            await this._save();
            skipAfterSaveHandlers = await shouldSkipAfterSaveHandlers();
        } finally {
            if (!skipAfterSaveHandlers) {
                this.trigger("on_saved_handlers");
            }
        }
    }
    async _save() {
        await Promise.all(this.trigger("on_ready_to_save_document_handlers"));
        this.dependencies.history.reset();
    }

    /**
     * Clone `el` and run the handlers needed to get it ready for save
     * @param {HTMLElement} el
     * @returns {HTMLElement}
     */
    prepareElementForSave(el) {
        const cleanedEl = el.cloneNode(true);
        this.processThrough("clean_for_save_processors", cleanedEl);
        escapeTextNodes(cleanedEl);
        return cleanedEl;
    }
}

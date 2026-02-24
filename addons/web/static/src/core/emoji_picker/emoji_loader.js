import { markRaw, reactive } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { escapeRegExp } from "@web/core/utils/strings";

/**
 * @typedef {{
 *  category: string;
 *  codepoints: string;
 *  emoticons: string[];
 *  keywords: string[];
 *  name: string;
 *  shortcodes: string[];
 * }} Emoji
 *
 * @typedef {{
 *  displayName: string;
 *  name: string;
 *  sortId: number;
 *  title: string;
 * }} EmojiCategory
 */

class EmojiLoader {
    // Main emoji data
    /** @type {EmojiCategory[]} */
    categories = [];
    /** @type {Emoji[]} */
    emojis = [];

    // Derived emoji data
    /** @type {Map<string, Emoji>} */
    emojiMap = markRaw(new Map());
    emojiRegex = DEFAULT_EMOJI_REGEX;

    // Loader metadata
    /** @type {Promise<EmojiLoader> | null} */
    loading = null;

    get loaded() {
        return this.emojis.length > 0;
    }

    /**
     * Returns the first short code associated to a given emoji value.
     *
     * @param {string} value
     */
    getShortCode(value) {
        return this.emojiMap.get(value)?.shortcodes?.[0] ?? "?";
    }

    /**
     * Entry point to load emoji data
     *
     * This function is memoized on the 'emojiLoade' singleton, so it will always
     * return the same promise.
     */
    load() {
        if (!this.loading) {
            this.loading = this._load().then(() => this);
        }
        return this.loading;
    }

    /**
     * Can be overridden on the `emojiLoader` instance to load a different bundle.
     */
    loadEmojiBundle() {
        return loadBundle("web.assets_emoji");
    }

    /**
     * @private
     */
    async _load() {
        try {
            await this.loadEmojiBundle();
            const { getCategories, getEmojis } = odoo.loader.modules.get(
                "@web/core/emoji_picker/emoji_data"
            );
            // Assign main data
            this.categories = markRaw(getCategories());
            this.emojis = markRaw(getEmojis());
        } catch {
            // Could be intentional (tour ended successfully while emoji still loading)
            // -> returns forever promise
            this.loading = null;
            return new Promise(() => {});
        }

        // Compute derived data
        const emojiRegexKeys = [];
        for (const emoji of this.emojis) {
            this.emojiMap.set(emoji.codepoints, emoji);
            for (const emoticon of emoji.emoticons) {
                this.emojiMap.set(emoticon, emoji);
            }
            for (const shortcode of emoji.shortcodes) {
                this.emojiMap.set(shortcode, emoji);
            }
            emojiRegexKeys.push(escapeRegExp(emoji.codepoints));
        }
        if (emojiRegexKeys.length) {
            // Sort to get composed emojis first
            emojiRegexKeys.sort((a, b) => b.length - a.length);
            this.emojiRegex = new RegExp(emojiRegexKeys.join("|"), "gu");
        }
    }
}

const DEFAULT_EMOJI_REGEX = /(?!)/gu;

export const emojiLoader = reactive(new EmojiLoader());

/** @type {EmojiLoader["load"]} */
export const loadEmoji = emojiLoader.load.bind(emojiLoader);

import { BasePlugin } from "@html_editor/base_plugin";
import { registry } from "@web/core/registry";
import { EMAIL_DESKTOP_DIMENSIONS, EMAIL_MOBILE_DIMENSIONS } from "../hooks";
import { containsAnyNonPhrasingContent } from "@html_editor/utils/dom_info";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { memoize } from "@web/core/utils/functions";
import { useShorthands } from "./hooks";

const DIMENSIONS = {
    desktop: EMAIL_DESKTOP_DIMENSIONS,
    mobile: EMAIL_MOBILE_DIMENSIONS,
};
export class ResponsivePlugin extends BasePlugin {
    static id = "ResponsivePlugin";
    static dependencies = ["layoutSnapshotCache"];
    resources = {
        reference_content_loaded_handlers: this.computeEmailHtmlStructure.bind(this),
        update_layout_dimensions_handlers: this.onUpdateLayoutDimensions.bind(this),
    };

    setup() {
        useShorthands(this, "layoutSnapshotCache", ["getBoundingClientRect"]);
        this.layoutDimensions = { width: 0, height: 0 };
        this.htmlStructures = new Map();
        this.phrasingContent = new Set();
        this.filterPhrasingContentNodes = memoize((node) => {
            const result = containsAnyNonPhrasingContent(node);
            if (!result) {
                for (const child of childNodes(node)) {
                    this.phrasingContent.add(child);
                }
            }
        });
    }

    // Algorithm to organize blocks between each other in a email sensible way.
    // It will completely disregard the style of the reference, and only
    // consider the desktop dimensions as well as the mobile dimensions of each
    // block. It will consider overlapping blocks as a whole if they overlap in
    // mobile and in desktop modes

    // does the algo need computed style or style? no, totally independent, it will
    // only do measurements => perfect hook
    computeEmailHtmlStructure() {
        this.parseWithLayout("desktop");
        this.parseWithLayout("mobile");
        // conclusion

        // simpler algo:
        // identify "horizontal clusters of blocks (flow elements)"
        // go through every node in the tree
        // mark its relation with previous and next element sibling -> problem
        // when identifying spans that are siblings of text nodes (or sometimes not)
        // and inside spans...
    }

    parseWithLayout(layoutType) {
        const originalDimensions = this.layoutDimensions;
        const dimensions = DIMENSIONS[layoutType];
        if (this.layoutDimensions.width !== dimensions.width) {
            this.config.updateLayoutDimensions(dimensions);
        }
        this.analyzePositioningLayout(layoutType);
        if (this.layoutDimensions.width !== originalDimensions.width) {
            this.config.updateLayoutDimensions(originalDimensions);
        }
    }

    getElementPositioningInfo(element) {
        return {
            element,
            parent: element.parentElement,
            previousElementSibling: element.previousElementSibling,
            nextElementSibling: element.nextElementSibling,
            elementRect: this.getBoundingClientRect(element),
            parentRect: this.getBoundingClientRect(element.parentElement),
            previousElementSiblingRect: element.previousElementSibling
                ? this.getBoundingClientRect(element.previousElementSibling)
                : undefined,
            nextElementSiblingRect: element.nextElementSibling
                ? this.getBoundingClientRect(element.nextElementSibling)
                : undefined,
        };
    }

    analyzePositioningLayout(layoutType) {
        const referenceToInfo = new WeakMap();
        const treeWalker = this.config.referenceDocument.createTreeWalker(
            this.config.reference,
            NodeFilter.SHOW_ELEMENT,
            (node) => {
                if (this.phrasingContent.has(node)) {
                    return NodeFilter.FILTER_REJECT;
                }
                // Disregard phasing content children
                // TODO EGGMAIL: filterPhrasingContentNodes is too restrictive, some phrasing content
                // could have been "dressed" as a block, do we want to support that?
                // if so, filterPhrasingContentNodes should be reworked in consequence.
                // -> Thinking about `img` blocks with `d-block` + some margin
                // -> maybe we should identify blocks with the display: block first ? Not sure what's the best approach here
                // what if there is a block element inside an inline element next to other inline elements? We have to dig deeper
                // to identify that situation
                // maybe elements which need to be flagged are those with a margin/padding value?
                // What we could do is apply the horizontal scan technique inside these block to identify if
                // a particular element has block-like behavior (img with margin, with d-block, etc) compared
                // to its peers
                this.filterPhrasingContentNodes(node);
                return NodeFilter.FILTER_ACCEPT;
            }
        );
        let el;
        while ((el = treeWalker.nextNode())) {
            // TODO EGGMAIL: ensure compatibility of this algo with RTL
            const {
                parent,
                previousElementSibling: prev,
                nextElementSibling: next,
                elementRect: elR,
                parentRect: parentR,
                previousElementSiblingRect: prevR,
                nextElementSiblingRect: nextR,
            } = this.getElementPositioningInfo(el);

            // method
            // compute overlapX and overlapY (min_right - max_left) > 0 | (min_bottom - max_top) > 0
            // normalize by min_width and min_height (xFrac and yFrac)
            // compute center distance (tie breaker)
            // decision
            // yFrac >= 0.5 and xFrac <= 0.3 (horizontal) => should almost never happen
            // yFrac <= 0.3 and xFrac >= 0.3 (vertical) => should almost never happen
            // tie breaker -> dx > dy (horizontal) | dy > dx (vertical)
            // -> normalize tie breaker? => most frequent
            // identify nesting (contains) => should never happen
            // identify high overlap (vertically + horizontally) => should never happen
            if (prev) {
                // compare alignment (vertical/horizontal)
                // mark parent as horizontal cluster if horizontal
                // margin between elements? (not sure it exists)
            } else {
                // check for left offset with parent (margin, padding, etc)
                // mark parent left padding value, check if already set
                // if parent right padding change in mobile mode, mark as horizontal cluster (potential offset-x)
                // take care of padding in relative units? Ignore?
            }
            if (next) {
                // compare alignment (vertical/horizontal)
                // mark parent as horizontal cluster if horizontal
            } else {
                // check for right offset with parent
                // mark parent right padding value, check if already set
                // if parent right padding change in mobile mode, mark as horizontal cluster (potential unfinished row)
                // take care of padding in relative units? Ignore?
            }
            // mark width and compare with mobile mode -> same => fixed width, different => % width or no width (start/end of row if some fixed width)

            // if sibling => comparison heuristic (left/right/top/bottom)

            // if no previousSibling => compare x position (left) with parent to check for offset
            // if no nextSibling => compare x position (right) with parent to check for isolated col-md-10

            // how to differenciate with padding?
            // -> if the padding value is not identical, could be approximated with a padding constant + an offset column.
            // -> Take care of padding values in % or other relative units.

            // how to differenciate with margin-auto?
            // -> does not even seem to work currently
            // -> investigate what is supposed to happen with that, maybe it shouldn't be there at all
            // -> all media queries from bootstrap seem to wrongly be there?
            // -> no usage of horizontal margins in the normal editor (to verify), and if they are detected, they should be handled as an "offset" so it's not wrong not to consider them I guess

            // Any variation in padding create a cluster candidate => to be determined later

            // do we need the mobile interpretation at this stage? Yes, it will
            // add some missing clusters without any conclusion, and we can easily check
            // if an element is a cluster in both, only in desktop, or only in mobile

            // TODO: verify that cluster identification works in following cases:
            // alert block (float),
            // container/row/col combo with offsets and unfinished rows
            // normal table
            // d-flex block without container/row/col?

            // if heuristics are correct -> start implementing "table" conversion
            // This should resolve almost all layout concerns (need to identify attributes/relevant css properties)
            // decide which properties we copy from class_to_style, more difficult when applying on tables
            // next issue would be images, fontawesome to image, and so on
            // handle outlook with ghost tables
            // handle colors
            // handle stylesheets in mail for usage of convert_inline
        }
        this.htmlStructures.set(layoutType, undefined);
    }

    onUpdateLayoutDimensions(layoutDimensions) {
        this.layoutDimensions = Object.assign({}, layoutDimensions);
    }
}

registry.category("mail-html-conversion-plugins").add(ResponsivePlugin.id, ResponsivePlugin);

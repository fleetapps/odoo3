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
            target: { el: element, rect: this.getBoundingClientRect(element) },
            parent: {
                el: element.parentElement,
                rect: this.getBoundingClientRect(element.parentElement),
            },
            next: element.nextElementSibling
                ? {
                      el: element.nextElementSibling,
                      rect: this.getBoundingClientRect(element.nextElementSibling),
                  }
                : undefined,
            prev: element.previousElementSibling
                ? {
                      el: element.previousElementSibling,
                      rect: this.getBoundingClientRect(element.previousElementSibling),
                  }
                : undefined,
        };
    }

    analyzeSiblingSpacing(siblingRect1, siblingRect2) {
        const { left: l1, right: r1, top: t1, bottom: b1 } = siblingRect1;
        const { left: l2, right: r2, top: t2, bottom: b2 } = siblingRect2;
        const dx = Math.max(l1, l2) - Math.min(r1, r2);
        const overlapX = Math.max(0, -dx);
        const dy = Math.max(t1, t2) - Math.min(b1, b2);
        const overlapY = Math.max(0, -dy);
        // TODO EGGMAIL: reconsider the 4x4 quadrant with 2 empty space cells,
        // sometimes it may be better to approximate to a row/column if the
        // spaces are not meaningful. And the reverse is also true, sometimes
        // it may be useful to handle a double overlap as rows/columns.
        return {
            row: !overlapX,
            column: !overlapY,
            spacingX: Math.max(0, dx),
            spacingY: Math.max(0, dy),
        };
    }

    // Idea here is to compare the spacing desktop vs mobile, to split into
    // fixed value, variable value, and define the best fitted layout strategy
    analyzeContainerSpacing(targetRect, containerRect) {
        const { left: l1, right: r1, top: t1, bottom: b1 } = targetRect;
        const { left: l2, right: r2, top: t2, bottom: b2 } = containerRect;
        return {
            spacingTop: Math.abs(t1 - t2),
            spacingLeft: Math.abs(l1 - l2),
            spacingBottom: Math.abs(b2 - b1),
            spacingRight: Math.abs(r2 - r1),
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
            const { target, parent, prev, next } = this.getElementPositioningInfo(el);
            // What are we searching for:
            // the parent is a row candidate if at least 2 of its children are "row" aligned, but they
            // are not necessarily DOM direct siblings
            // We are not considering position-absolute elements or other positioned elements that break the
            // DOM flow (only exception = simple float)

            // 
            if (prev) {
                // the parent is a row candidate if at least 2 of its children are "row" aligned

                // compare alignment (vertical/horizontal)
                // mark parent as horizontal cluster if horizontal
                // gaps between elements
            } else {
                // there is no guarantee that the first DOM child is the leftmost one

                // check for left offset with parent (margin, padding, etc)
                // mark parent left padding value, check if already set
                // if parent right padding change in mobile mode, mark as horizontal cluster (potential offset-x)
                // take care of padding in relative units? Ignore?
            }
            if (next) {
                // compare alignment (vertical/horizontal)
                // mark parent as horizontal cluster if horizontal
            } else {
                // there is no guarantee that the last DOM child is the rightmost one, especially
                // if it is a single row partially wrapped

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

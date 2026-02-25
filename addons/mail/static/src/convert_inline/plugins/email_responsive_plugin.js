import { BasePlugin } from "@html_editor/base_plugin";
import { registry } from "@web/core/registry";
import { EMAIL_DESKTOP_DIMENSIONS, EMAIL_MOBILE_DIMENSIONS } from "../hooks";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { memoize } from "@web/core/utils/functions";
import { useShorthands } from "./hooks";
import { Band } from "./responsive_utils";

const BLOCK_TAG_NAMES = [
    "ADDRESS",
    "ARTICLE",
    "ASIDE",
    "BLOCKQUOTE",
    "DETAILS",
    "DIALOG",
    "DD",
    "DIV",
    "DL",
    "DT",
    "FIELDSET",
    "FIGCAPTION",
    "FIGURE",
    "FOOTER",
    "FORM",
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
    "HEADER",
    "HGROUP",
    "HR",
    "LI",
    "MAIN",
    "NAV",
    "OL",
    "P",
    "PRE",
    "SECTION",
    "TABLE",
    "UL",
    "SELECT",
    "OPTION",
    "TR",
    "TD",
    "TBODY",
    "THEAD",
    "TH",
];
const DIMENSIONS = {
    desktop: EMAIL_DESKTOP_DIMENSIONS,
    mobile: EMAIL_MOBILE_DIMENSIONS,
};

function getDX({ left: l1, right: r1 }, { left: l2, right: r2 }) {
    return Math.max(l1, l2) - Math.min(r1, r2);
}

function getDY({ top: t1, bottom: b1 }, { top: t2, bottom: b2 }) {
    return Math.max(t1, t2) - Math.min(b1, b2);
}

function getOverlapX(rect1, rect2) {
    const dx = getDX(rect1, rect2);
    return Math.max(0, -dx);
}

function getOverlapY(rect1, rect2) {
    const dy = getDY(rect1, rect2);
    return Math.max(0, -dy);
}

function getGapX(rect1, rect2) {
    const dx = getDX(rect1, rect2);
    return Math.max(0, dx);
}

function getGapY(rect1, rect2) {
    const dy = getDY(rect1, rect2);
    return Math.max(0, dy);
}

export class ResponsivePlugin extends BasePlugin {
    static id = "ResponsivePlugin";
    static dependencies = ["layoutSnapshotCache"];
    resources = {
        reference_content_loaded_handlers: this.computeEmailHtmlStructure.bind(this),
        update_layout_dimensions_handlers: this.onUpdateLayoutDimensions.bind(this),
    };

    setup() {
        useShorthands(this, "layoutSnapshotCache", [
            "getBoundingClientRect",
            "getNodeClusterRange",
            "getStylePropertyValue",
        ]);
        this.layoutDimensions = { width: 0, height: 0 };
        this.layoutToBands = new Map(); // layoutName (desktop/mobile) -> map: node -> bands
        this.ignoredInlineNodes = new WeakSet();
        this.filterInlineNodes = memoize((node) => {
            const subNodes = [];
            let hasSomeBlock = false;
            let child = node.firstChild;
            while (child) {
                if (!hasSomeBlock && this.isBlock(child)) {
                    hasSomeBlock = true;
                }
                subNodes.push(child);
                child = child.nextSibling;
            }
            if (!hasSomeBlock) {
                for (const child of subNodes) {
                    this.ignoredInlineNodes.add(child);
                }
            }
        });
    }

    /**
     * Custom `isBlock` function using the email_layout_snapshot_cache
     */
    isBlock(node) {
        if (!node || node.nodeType !== Node.ELEMENT_NODE || !node.isConnected) {
            return false;
        }
        if (node.nodeName === "BR") {
            // see html_editor isBlock for explanation (browser compatibility)
            return false;
        }
        const display = this.getStylePropertyValue(node, "display");
        if (display && display !== "none") {
            return !display.includes("inline") && display !== "contents";
        }
        return BLOCK_TAG_NAMES.includes(node.nodeName);
    }

    // Algorithm to organize blocks between each other in a email sensible way.
    // It will completely disregard the style of the reference, and only
    // consider the desktop dimensions as well as the mobile dimensions of each
    // block. It will consider overlapping blocks as a whole if they overlap in
    // mobile and in desktop modes

    computeEmailHtmlStructure() {
        this.parseWithLayout("desktop");
        this.parseWithLayout("mobile");
        // TODO EGGMAIL: create final layout based on measured layouts
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

    analyzeSiblingSpacing(siblingRect1, siblingRect2) {
        // TODO EGGMAIL: reconsider the 4x4 quadrant with 2 empty space cells,
        // sometimes it may be better to approximate to a row/column if the
        // spaces are not meaningful. And the reverse is also true, sometimes
        // it may be useful to handle a double overlap as rows/columns.
        return {
            row: !getOverlapX(siblingRect1, siblingRect2),
            column: !getOverlapY(siblingRect1, siblingRect2),
            gapX: getGapX(siblingRect1, siblingRect2),
            gapY: getGapY(siblingRect1, siblingRect2),
        };
    }

    // Idea here is to compare the spacing desktop vs mobile, to split into
    // fixed value, variable value, and define the best fitted layout strategy
    analyzeContainerSpacing(innerRect, outerRect) {
        const { left: l1, right: r1, top: t1, bottom: b1 } = innerRect;
        const { left: l2, right: r2, top: t2, bottom: b2 } = outerRect;
        return {
            spacingTop: Math.abs(t1 - t2),
            spacingLeft: Math.abs(l1 - l2),
            spacingBottom: Math.abs(b2 - b1),
            spacingRight: Math.abs(r2 - r1),
        };
    }

    /**
     * TODO EGGMAIL: DISCLAIMER:
     * Only consider clusters of elements that are direct childNodes of their parent
     * any style that disregard the DOM hierarchy (eg position: absolute) is not
     * supported
     */
    computeClusterInfos(parent) {
        const subNodes = childNodes(parent);
        const clusterInfos = subNodes.reduce((accumulator, node) => {
            const isBlock = this.isBlock(node);
            const prevClusterInfo = accumulator.at(-1);
            const clusterInfo =
                isBlock || !prevClusterInfo || prevClusterInfo.isBlock
                    ? {
                          nodes: [node],
                          isBlock,
                      }
                    : prevClusterInfo;
            if (clusterInfo !== prevClusterInfo) {
                accumulator.push(clusterInfo);
            } else {
                clusterInfo.nodes.push(node);
            }
            return accumulator;
        }, []);
        return clusterInfos;
    }

    computeBands(clusterInfos) {
        let bands = new Set();
        for (const clusterInfo of clusterInfos) {
            const nodes = clusterInfo.nodes;
            clusterInfo.rect = this.getBoundingClientRect(
                clusterInfo.isBlock
                    ? clusterInfo.nodes[0]
                    : this.getNodeClusterRange(nodes.at(0), nodes.at(-1))
            );
            if (clusterInfo.rect.height === 0 || clusterInfo.rect.width === 0) {
                continue;
            }
            const bandCandidates = [];
            for (const band of bands) {
                if (getOverlapY(band, clusterInfo.rect)) {
                    bandCandidates.push(band);
                }
            }
            let band = bandCandidates.shift();
            if (!band) {
                band = new Band();
                bands.add(band);
            }
            bands = bands.difference(new Set(bandCandidates));
            for (const candidate of bandCandidates) {
                band.merge(candidate);
            }
            band.addClusterInfo(clusterInfo);
        }
        for (const band of bands) {
            // TODO EGGMAIL: sorting is not stable (clusters with same center position are "identical")
            band.clusterInfos.sort((clusterInfo1, clusterInfo2) => {
                const { left: l1, width: w1 } = clusterInfo1;
                const { left: l2, width: w2 } = clusterInfo2;
                return l1 + w1 / 2 - (l2 + w2 / 2);
            });
        }
        return Array.from(bands).sort((band1, band2) => band1.top - band2.top);
    }

    analyzePositioningLayout(layoutType) {
        const nodeToBands = new WeakMap();
        this.layoutToBands.set(layoutType, nodeToBands);
        const treeWalker = this.config.referenceDocument.createTreeWalker(
            this.config.reference,
            NodeFilter.SHOW_ELEMENT,
            (node) => {
                if (this.ignoredInlineNodes.has(node)) {
                    return NodeFilter.FILTER_REJECT;
                }
                this.filterInlineNodes(node);
                return NodeFilter.FILTER_ACCEPT;
            }
        );
        let el = treeWalker.root;
        do {
            const clusterInfos = this.computeClusterInfos(el);
            const bands = this.computeBands(clusterInfos);
            nodeToBands.set(el, bands);
        } while ((el = treeWalker.nextNode()));

        // while ((el = treeWalker.nextNode())) {

        //     if (prev) {
        //         // the parent is a row candidate if at least 2 of its children are "row" aligned

        //         // compare alignment (vertical/horizontal)
        //         // mark parent as horizontal cluster if horizontal
        //         // gaps between elements
        //     } else {

        //         // check for left offset with parent (margin, padding, etc)
        //         // mark parent left padding value, check if already set
        //         // if parent right padding change in mobile mode, mark as horizontal cluster (potential offset-x)
        //         // take care of padding in relative units? Ignore?
        //     }
        //     if (next) {
        //         // compare alignment (vertical/horizontal)
        //         // mark parent as horizontal cluster if horizontal
        //     } else {
        //         // there is no guarantee that the last DOM child is the rightmost one, especially
        //         // if it is a single row partially wrapped

        //         // check for right offset with parent
        //         // mark parent right padding value, check if already set
        //         // if parent right padding change in mobile mode, mark as horizontal cluster (potential unfinished row)
        //         // take care of padding in relative units? Ignore?
        //     }
        //     // mark width and compare with mobile mode -> same => fixed width, different => % width or no width (start/end of row if some fixed width)

        //     // if sibling => comparison heuristic (left/right/top/bottom)

        //     // if no previousSibling => compare x position (left) with parent to check for offset
        //     // if no nextSibling => compare x position (right) with parent to check for isolated col-md-10

        //     // how to differenciate with padding?
        //     // -> if the padding value is not identical, could be approximated with a padding constant + an offset column.
        //     // -> Take care of padding values in % or other relative units.

        //     // how to differenciate with margin-auto?
        //     // -> does not even seem to work currently
        //     // -> investigate what is supposed to happen with that, maybe it shouldn't be there at all
        //     // -> all media queries from bootstrap seem to wrongly be there?
        //     // -> no usage of horizontal margins in the normal editor (to verify), and if they are detected, they should be handled as an "offset" so it's not wrong not to consider them I guess

        //     // Any variation in padding create a cluster candidate => to be determined later

        //     // do we need the mobile interpretation at this stage? Yes, it will
        //     // add some missing clusters without any conclusion, and we can easily check
        //     // if an element is a cluster in both, only in desktop, or only in mobile

        //     // TODO: verify that cluster identification works in following cases:
        //     // alert block (float),
        //     // container/row/col combo with offsets and unfinished rows
        //     // normal table
        //     // d-flex block without container/row/col?

        //     // if heuristics are correct -> start implementing "table" conversion
        //     // This should resolve almost all layout concerns (need to identify attributes/relevant css properties)
        //     // decide which properties we copy from class_to_style, more difficult when applying on tables
        //     // next issue would be images, fontawesome to image, and so on
        //     // handle outlook with ghost tables
        //     // handle colors
        //     // handle stylesheets in mail for usage of convert_inline
        // }
    }

    onUpdateLayoutDimensions(layoutDimensions) {
        this.layoutDimensions = Object.assign({}, layoutDimensions);
    }
}

registry.category("mail-html-conversion-plugins").add(ResponsivePlugin.id, ResponsivePlugin);

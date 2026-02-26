import { BasePlugin } from "@html_editor/base_plugin";
import { registry } from "@web/core/registry";
import { EMAIL_DESKTOP_DIMENSIONS, EMAIL_MOBILE_DIMENSIONS } from "../hooks";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { memoize } from "@web/core/utils/functions";
import { useShorthands } from "./hooks";
import { Band, getOverlapY } from "./responsive_utils";

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
        this.layoutStrategies = new WeakMap(); // node -> strategy
        this.ignoredInlineNodes = new WeakSet();
        this.filterInlineNodes = memoize((node) => {
            // TODO EGGMAIL: evaluate if memoize makes sense here or if we should
            // independently compute ignoredInlineNodes depending on the layout,
            // to capture nodes that are inline in one layout and block in another
            // (should not happen, but who knows)
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

    createLayoutTreeWalker() {
        return this.config.referenceDocument.createTreeWalker(
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
        this.applyLayoutStrategies();
        // TODO EGGMAIL: create final layout based on measured layouts
    }

    applyDefaultStrategy({ parent, layoutToBands }) {
        const strategy = undefined;
        return strategy;
    }

    applyLayoutStrategies() {
        const treeWalker = this.createLayoutTreeWalker();
        let el = treeWalker.root;
        do {
            const layoutToBands = new Map(); // map layout to bands for this el
            for (const layout of this.layoutToBands.keys()) {
                layoutToBands.set(layout, this.layoutToBands.get(layout).get(el));
            }
            let strategy;
            const output = { strategy };
            const args = { parent: el, layoutToBands };
            if (this.delegateTo("choose_layout_strategy_overrides", args, output)) {
                ({ strategy } = output);
            } else {
                strategy = this.applyDefaultStrategy(args);
            }
            this.layoutStrategies.set(el, strategy);
        } while ((el = treeWalker.nextNode()));
    }

    parseWithLayout(layoutType) {
        const originalDimensions = this.layoutDimensions;
        const dimensions = DIMENSIONS[layoutType];
        if (this.layoutDimensions.width !== dimensions.width) {
            this.config.updateLayoutDimensions(dimensions);
        }
        this.computeLayoutBands(layoutType);
        if (this.layoutDimensions.width !== originalDimensions.width) {
            this.config.updateLayoutDimensions(originalDimensions);
        }
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

    computeClusterBands(clusterInfos) {
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
            // TODO EGGMAIL: sorting is not perfect (clusters with same center position are "identical")
            band.clusterInfos.sort((clusterInfo1, clusterInfo2) => {
                const { left: l1, width: w1 } = clusterInfo1;
                const { left: l2, width: w2 } = clusterInfo2;
                return l1 + w1 / 2 - (l2 + w2 / 2);
            });
        }
        return Array.from(bands).sort((band1, band2) => band1.top - band2.top);
    }

    computeLayoutBands(layoutType) {
        const nodeToBands = new WeakMap();
        this.layoutToBands.set(layoutType, nodeToBands);
        const treeWalker = this.createLayoutTreeWalker();
        let el = treeWalker.root;
        do {
            const clusterInfos = this.computeClusterInfos(el);
            const bands = this.computeClusterBands(clusterInfos);
            nodeToBands.set(el, bands);
        } while ((el = treeWalker.nextNode()));
    }

    onUpdateLayoutDimensions(layoutDimensions) {
        this.layoutDimensions = Object.assign({}, layoutDimensions);
    }
}

registry.category("mail-html-conversion-plugins").add(ResponsivePlugin.id, ResponsivePlugin);

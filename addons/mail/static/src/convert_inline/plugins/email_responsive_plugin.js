import { BasePlugin } from "@html_editor/base_plugin";
import { registry } from "@web/core/registry";
import { EMAIL_DESKTOP_DIMENSIONS, EMAIL_MOBILE_DIMENSIONS } from "../hooks";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { memoize } from "@web/core/utils/functions";
import { useShorthands } from "./hooks";
import {
    Band,
    LayoutCluster,
    getOverlapY,
    LayoutBlock,
    getContainerPadding,
} from "./responsive_utils";

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

export class ResponsivePlugin extends BasePlugin {
    static id = "ResponsivePlugin";
    static dependencies = ["layoutSnapshotCache", "vDomPlugin"];
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
        useShorthands(this, "vDomPlugin", ["getNodeInfo"]);
        this.layoutDimensions = { width: 0, height: 0 };
        this.layoutToFilters = new Map(); // layoutDimensions (desktop/mobile) -> filterInlineNodes function
        this.layoutToBlocks = new Map(); // layoutDimensions (desktop/mobile) -> map: node -> LayoutBlock
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

    // TODO NOW: optional filter based on layout dimensions + new filter for
    // applying strategies
    createReferenceTreeWalker(filter = () => NodeFilter.FILTER_ACCEPT) {
        return this.config.referenceDocument.createTreeWalker(
            this.config.reference,
            NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
            filter
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
        this.parseWithDimensions(EMAIL_DESKTOP_DIMENSIONS);
        this.parseWithDimensions(EMAIL_MOBILE_DIMENSIONS);
        this.applyLayoutStrategies();
        // TODO EGGMAIL: create final layout based on measured layouts
    }

    getDefaultStrategy({ parent, layoutToBlocks }) {
        const strategy = undefined;
        return strategy;
    }

    applyLayoutStrategies() {
        // TODO EGGMAIL: create a tree walker to go over every node in the reference
        // every node should have a "strategy" resulting in a fragment, even if
        // it's ignore/do nothing/skip descendants
        // treeWalker could/should ignore descendants of nodes where the strategy
        // is to ignore descendants
        // review current rendering loop and how it applies fragments
        const rejectedNodes = new WeakSet();
        const treeWalker = this.createReferenceTreeWalker((node) => {
            if (rejectedNodes.has(node)) {
                return NodeFilter.FILTER_REJECT;
            }
            return NodeFilter.FILTER_ACCEPT;
        });
        let node = treeWalker.root;
        do {
            const layoutToBlocks = new Map(); // map layout to bands for this el
            for (const layoutDimensions of this.layoutToBlocks.keys()) {
                layoutToBlocks.set(
                    layoutDimensions,
                    this.layoutToBlocks.get(layoutDimensions).get(node)
                );
            }
            let strategy;
            const output = { strategy };
            const args = { node, layoutToBlocks };
            if (this.delegateTo("choose_layout_strategy_overrides", args, output)) {
                ({ strategy } = output);
            } else {
                strategy = this.getDefaultStrategy(args);
            }
            const nodeInfo = this.getNodeInfo(node);
            nodeInfo.setRenderStrategy(strategy);
            if (strategy.rejectSubTree) {
                let child = node.firstChild;
                while (child) {
                    rejectedNodes.add(child);
                    child = child.nextSibling;
                }
            }
        } while ((node = treeWalker.nextNode()));
    }

    parseWithDimensions(dimensions) {
        const ignoredInlineNodes = new WeakSet();
        const filterInlineNodes = memoize((node) => {
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
                    ignoredInlineNodes.add(child);
                }
            }
        });
        this.layoutToFilters.set(dimensions, (node) => {
            if (ignoredInlineNodes.has(node)) {
                return NodeFilter.FILTER_REJECT;
            }
            filterInlineNodes(node);
            return NodeFilter.FILTER_ACCEPT;
        });
        const originalDimensions = this.layoutDimensions;
        if (this.layoutDimensions.width !== dimensions.width) {
            this.config.updateLayoutDimensions(dimensions);
        }
        this.computeLayoutBlocks();
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
    computeLayoutClusters(parent) {
        const subNodes = childNodes(parent);
        const layoutClusters = subNodes.reduce((accumulator, node) => {
            const isBlock = this.isBlock(node);
            const prevLayoutCluster = accumulator.at(-1);
            const layoutCluster =
                isBlock || !prevLayoutCluster || prevLayoutCluster.isBlock
                    ? new LayoutCluster([node], isBlock)
                    : prevLayoutCluster;
            if (layoutCluster !== prevLayoutCluster) {
                accumulator.push(layoutCluster);
            } else {
                layoutCluster.nodes.push(node);
            }
            return accumulator;
        }, []);
        return layoutClusters;
    }

    computeClusterBands(layoutClusters) {
        let bands = new Set();
        for (const layoutCluster of layoutClusters) {
            const nodes = layoutCluster.nodes;
            layoutCluster.rect = this.getBoundingClientRect(
                layoutCluster.isBlock
                    ? layoutCluster.nodes[0]
                    : this.getNodeClusterRange(nodes.at(0), nodes.at(-1))
            );
            if (layoutCluster.rect.height === 0 || layoutCluster.rect.width === 0) {
                continue;
            }
            const bandCandidates = [];
            for (const band of bands) {
                if (getOverlapY(band, layoutCluster.rect)) {
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
            band.addLayoutCluster(layoutCluster);
        }
        for (const band of bands) {
            // TODO EGGMAIL: sorting is not perfect (clusters with same center position are "identical")
            band.layoutClusters.sort((layoutCluster1, layoutCluster2) => {
                const { left: l1, width: w1 } = layoutCluster1;
                const { left: l2, width: w2 } = layoutCluster2;
                return l1 + w1 / 2 - (l2 + w2 / 2);
            });
        }
        return Array.from(bands).sort((band1, band2) => band1.top - band2.top);
    }

    computeLayoutBlock(element, bands) {
        const layoutBlock = new LayoutBlock(element, bands, this.getBoundingClientRect(element));
        const firstBand = layoutBlock.bands.at(0);
        const lastBand = layoutBlock.bands.at(-1);
        const rect = layoutBlock.rect;
        const bandsRect = {
            top: firstBand?.top ?? rect.top,
            bottom: lastBand?.bottom ?? rect.bottom,
        };
        for (const band of bands) {
            for (const layoutCluster of band.layoutClusters) {
                if (bandsRect.left === undefined || layoutCluster.rect.left < bandsRect.left) {
                    bandsRect.left = layoutCluster.rect.left;
                }
                if (bandsRect.right === undefined || layoutCluster.rect.right > bandsRect.right) {
                    bandsRect.right = layoutCluster.rect.right;
                }
            }
        }
        bandsRect.left ??= rect.left;
        bandsRect.right ??= rect.right;
        layoutBlock.padding = getContainerPadding(bandsRect, rect);
        return layoutBlock;
    }

    computeLayoutBlocks() {
        const nodeToBlocks = new WeakMap();
        this.layoutToBlocks.set(this.layoutDimensions, nodeToBlocks);
        const filterInlineNodes = this.layoutToFilters.get(this.layoutDimensions);
        const treeWalker = this.createReferenceTreeWalker(filterInlineNodes);
        let el = treeWalker.root;
        do {
            const layoutClusters = this.computeLayoutClusters(el);
            const bands = this.computeClusterBands(layoutClusters);
            const layoutBlock = this.computeLayoutBlock(el, bands);
            nodeToBlocks.set(el, layoutBlock);
        } while ((el = treeWalker.nextNode()));
    }

    onUpdateLayoutDimensions(layoutDimensions) {
        this.layoutDimensions = Object.assign({}, layoutDimensions);
    }
}

registry.category("mail-html-conversion-plugins").add(ResponsivePlugin.id, ResponsivePlugin);

import { renderToFragment } from "@web/core/utils/render";

export function getDX({ left: l1, right: r1 }, { left: l2, right: r2 }) {
    return Math.max(l1, l2) - Math.min(r1, r2);
}

export function getDY({ top: t1, bottom: b1 }, { top: t2, bottom: b2 }) {
    return Math.max(t1, t2) - Math.min(b1, b2);
}

export function getOverlapX(rect1, rect2) {
    const dx = getDX(rect1, rect2);
    return Math.max(0, -dx);
}

export function getOverlapY(rect1, rect2) {
    const dy = getDY(rect1, rect2);
    return Math.max(0, -dy);
}

export function getGapX(rect1, rect2) {
    const dx = getDX(rect1, rect2);
    return Math.max(0, dx);
}

export function getGapY(rect1, rect2) {
    const dy = getDY(rect1, rect2);
    return Math.max(0, dy);
}

export function getSiblingSpacing(siblingRect1, siblingRect2) {
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
export function getContainerPadding(innerRect, outerRect) {
    const { left: li, right: ri, top: ti, bottom: bi } = innerRect;
    const { left: lo, right: ro, top: to, bottom: bo } = outerRect;
    // TODO EGGMAIL: reconsider: do not allow inner elements to overflow outside
    // of their parent (such overflow will be ignored)
    return {
        top: Math.max(0, ti - to),
        left: Math.max(0, li - lo),
        bottom: Math.max(0, bo - bi),
        right: Math.max(0, ro - ri),
    };
}

export class Band {
    // implicit positioning:
    // margin-left => band.left - (layoutBlock.left + layoutBlock.padding.left)
    // margin-right same
    // gapY with previous/next band
    top;
    bottom;
    layoutClusters = [];

    addLayoutCluster(layoutCluster) {
        this.layoutClusters.push(layoutCluster);
        this.top ??= layoutCluster.rect.top;
        this.top = Math.min(this.top, layoutCluster.rect.top);
        this.bottom ??= layoutCluster.rect.bottom;
        this.bottom = Math.max(this.bottom, layoutCluster.rect.bottom);
    }

    merge(band) {
        for (const layoutCluster of band.layoutClusters) {
            this.addLayoutCluster(layoutCluster);
        }
    }
}

export class LayoutCluster {
    // implicit positioning:
    // margin-top => cluster.top - band.top
    // margin-bottom => same
    // gapX with previous/next cluster
    nodes = [];
    isBlock;
    rect;
    constructor(nodes, isBlock) {
        this.nodes = nodes;
        this.isBlock = isBlock;
    }
}

export class LayoutBlock {
    element;
    bands = [];
    rect;
    padding = { top: 0, bottom: 0, left: 0, right: 0 };
    constructor(element, bands, rect) {
        this.element = element;
        this.bands = bands;
        this.rect = rect;
    }
}

export class LayoutStrategy {
    parent;

    constructor(type, parent) {
        this.parent = parent;
        this.type = type;
    }

    render(extraContext = {}) {
        return renderToFragment(this.template, {
            strategy: this,
            ...extraContext,
        });
    }
}

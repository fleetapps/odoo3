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
export function getContainerSpacing(innerRect, outerRect) {
    const { left: l1, right: r1, top: t1, bottom: b1 } = innerRect;
    const { left: l2, right: r2, top: t2, bottom: b2 } = outerRect;
    return {
        spacingTop: Math.abs(t1 - t2),
        spacingLeft: Math.abs(l1 - l2),
        spacingBottom: Math.abs(b2 - b1),
        spacingRight: Math.abs(r2 - r1),
    };
}

export class Band {
    top;
    bottom;
    clusterInfos = [];

    addClusterInfo(clusterInfo) {
        this.clusterInfos.push(clusterInfo);
        this.top ??= clusterInfo.rect.top;
        this.top = Math.min(this.top, clusterInfo.rect.top);
        this.bottom ??= clusterInfo.rect.bottom;
        this.bottom = Math.max(this.bottom, clusterInfo.rect.bottom);
    }

    merge(band) {
        for (const clusterInfo of band.clusterInfos) {
            this.addClusterInfo(clusterInfo);
        }
    }
}

export class LayoutStrategy {
    ancestors = [];
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

import { BasePlugin } from "@html_editor/base_plugin";
import { registry } from "@web/core/registry";
import { generateLonghands } from "@mail/convert_inline/style_utils";

const BACKGROUND_VARIANTS = ["color", "image", "repeat", "size"];
const CONTOUR_VARIANTS = ["width", "style", "color"];
const DIRECTION_VARIANTS = ["top", "right", "bottom", "left"];
const FONT_VARIANTS = ["family", "size", "style", "weight"];
const DOM_RECT_PROPERTIES = ["x", "y", "width", "height", "top", "right", "bottom", "left"];

export class LayoutSnapshotCachePlugin extends BasePlugin {
    static id = "layoutSnapshotCache";
    static shared = [
        "getBoundingClientRect",
        "getComputedStyle",
        "getNodeClusterRange",
        "getStylePropertyValue",
        "getStyleHeight",
        "getStyleWidth",
        "registerStyleProperty",
    ];

    resources = {
        // typical shorthands for emails (prefer usage of longhand names for
        // these properties). They are recorded by default in a getComputedStyle
        // snapshot
        shorthand_to_longhand_properties: {
            background: new Set(generateLonghands("background", [BACKGROUND_VARIANTS])),
            border: new Set(generateLonghands("border", [DIRECTION_VARIANTS, CONTOUR_VARIANTS])),
            font: new Set(generateLonghands("font", [FONT_VARIANTS])),
            margin: new Set(generateLonghands("margin", [DIRECTION_VARIANTS])),
            outline: new Set(generateLonghands("outline", [CONTOUR_VARIANTS])),
            padding: new Set(generateLonghands("padding", [DIRECTION_VARIANTS])),
        },
        // longhands recorded by default in a getComputedStyle snapshot
        longhand_properties: [
            "border-collapse",
            "box-sizing",
            "color",
            "display",
            "height",
            "line-height",
            "position",
            "text-decoration",
            "text-transform",
            "text-align",
            "vertical-align",
            "width",
        ],
        update_layout_dimensions_handlers: this.onUpdateLayoutDimensions.bind(this),
    };

    setup() {
        this.styleProperties = new Set(); // properties to register in a snapshot
        this.computedStylesMap = new Map(); // dimensions to WeakMap of element to computed snapshot proxy
        this.domRectProperties = new Set(DOM_RECT_PROPERTIES); // properties of a DOMRect
        this.boundingClientRectsMap = new Map(); // dimensions to WeakMap of element/range to bounding client rect snapshot proxy
        this.nodeClusterRangeMap = new WeakMap(); // node to range of all contiguous non-element nodes in a cluster
        this.dimensionsKey = "undefined";
        this.computedStylesMap.set(this.dimensionsKey, new WeakMap());
        this.boundingClientRectsMap.set(this.dimensionsKey, new WeakMap());
        this.setupProperties();
    }

    setupShorthandToLonghand() {
        this.shorthandToLonghand = this.getResource("shorthand_to_longhand_properties").reduce(
            (shortHandToLonghand, current) => {
                for (const property in current) {
                    shortHandToLonghand[property] = current[property].union(
                        shortHandToLonghand[property] ?? new Set()
                    );
                }
                return shortHandToLonghand;
            },
            {}
        );
    }

    setupProperties() {
        this.setupShorthandToLonghand();
        for (const propertyName in this.shorthandToLonghand) {
            this.registerStyleProperty(propertyName);
        }
        const longhandProperties = this.getResource("longhand_properties");
        for (const propertyName of longhandProperties) {
            this.registerStyleProperty(propertyName);
        }
    }

    onUpdateLayoutDimensions({ width }) {
        this.dimensionsKey = `${width}`;
        if (!this.computedStylesMap.has(this.dimensionsKey)) {
            this.computedStylesMap.set(this.dimensionsKey, new WeakMap());
        }
        if (!this.boundingClientRectsMap.has(this.dimensionsKey)) {
            this.boundingClientRectsMap.set(this.dimensionsKey, new WeakMap());
        }
    }

    cachedComputedStyleProxyHandler(element) {
        return {
            set: () => false,
            deleteProperty: () => false,
            get: (target, key, receiver) => {
                if (typeof key === "string" && !(key in target)) {
                    this.registerStyleProperty(key);
                    this.getStyleSnapshot(element, target);
                }
                return Reflect.get(target, key, receiver);
            },
        };
    }

    cachedBoundingClientRectProxyHandler(cluster) {
        return {
            set: () => false,
            deleteProperty: () => false,
            get: (target, key, receiver) => {
                if (
                    typeof key === "string" &&
                    !(key in target) &&
                    this.domRectProperties.has(key)
                ) {
                    this.getBoundingClientRectSnapshot(cluster, target);
                }
                return Reflect.get(target, key, receiver);
            },
        };
    }

    registerStyleProperty(propertyName) {
        if (propertyName in this.shorthandToLonghand) {
            const propertyNames = this.shorthandToLonghand[propertyName];
            for (const longHandProperty of propertyNames) {
                this.registerStyleProperty(longHandProperty);
            }
        }
        if (!this.styleProperties.has(propertyName)) {
            this.styleProperties.add(propertyName);
        }
    }

    getStyleSnapshot(element, styleSnapshot = {}) {
        const computedStyle = element.ownerDocument.defaultView.getComputedStyle(element);
        for (const propertyName of this.styleProperties) {
            if (!(propertyName in styleSnapshot)) {
                styleSnapshot[propertyName] = computedStyle.getPropertyValue(propertyName);
            }
        }
        return styleSnapshot;
    }

    /**
     * @param {HTMLElement|Range} cluster
     * @param {Object} rectSnapshot
     * @returns {DOMRect}
     */
    getBoundingClientRectSnapshot(cluster, rectSnapshot = {}) {
        const boundingClientRect = cluster.getBoundingClientRect();
        for (const propertyName of this.domRectProperties) {
            if (!(propertyName in rectSnapshot)) {
                rectSnapshot[propertyName] = boundingClientRect[propertyName];
            }
        }
        return rectSnapshot;
    }

    getNodeClusterRange(node) {
        let range;
        const isInReference = this.config.referenceDocument.contains(node);
        if (isInReference) {
            range = this.nodeClusterRangeMap.get(node);
        }
        if (!range) {
            range = this.config.referenceDocument.createRange();
            let firstNode = node;
            while (firstNode.previousSibling.nodeType !== Node.ELEMENT_NODE) {
                firstNode = firstNode.previousSibling;
            }
            let lastNode = node;
            while (lastNode.nextSibling.nodeType !== Node.ELEMENT_NODE) {
                lastNode = lastNode.nextSibling;
            }
            range.setStart(firstNode, 0);
            range.setEnd(lastNode, lastNode.length);
        }
        if (isInReference) {
            this.nodeClusterRangeMap.set(node, range);
        }
        return range;
    }

    /**
     * Returns a cached view of `getComputedStyle`. The cache is long-lived if the element is in
     * the reference HTML (associated with a given dimensionsKey), because the reference dimensions
     * are fixed relative to that dimensionsKey, and the cache can be reused if
     * this function is called on the same element.
     * The cache is short-lived otherwise (it has its own scope), and a new call to this function
     * will essentially generate a call to `getComputedStyle`.
     *
     * @param {HTMLElement} element
     * @returns {Object} cached style
     */
    getComputedStyle(element) {
        if (this.config.referenceDocument.contains(element)) {
            // Only the style of an element inside the referenceDocument can be cached, as
            // the HTML and CSS content inside that document are fixed during conversion.
            const cachedStyle =
                this.computedStylesMap.get(this.dimensionsKey).get(element) ??
                new Proxy({}, this.cachedComputedStyleProxyHandler(element));
            this.computedStylesMap.get(this.dimensionsKey).set(element, cachedStyle);
            return cachedStyle;
        }
        return new Proxy({}, this.cachedComputedStyleProxyHandler(element));
    }

    /**
     * Returns a cached view of `getBoundingClientRect`. The cache is long-lived if the node is in
     * the reference HTML (associated with a given dimensionsKey), because the reference dimensions
     * are fixed relative to that dimensionsKey, and the cache can be reused if
     * this function is called on the same node.
     * The cache is short-lived otherwise (it has its own scope), and a new call to this function
     * will essentially generate a call to `getBoundingClientRect`.
     * For non-element nodes, the returned boundingClientRect is the one generated from the range
     * related to the cluster of contiguous non-element nodes, as finer detailing is not needed for
     * the email layout.
     *
     * @param {Node} node
     * @returns {Object} cached bounding client rect
     */
    getBoundingClientRect(node) {
        let cluster = node;
        // TODO EGGMAIL NOW: change condition based on inline-not inline
        // what to do about inline blocks?
        // other idea -> keep as is, create a new function receiving an already
        // created range, cache it, and return the boundingClientRect.
        // adapt this function to only create the range for a single non-element node
        // and use the other for multiple nodes -> cleaner api, no surprise.
        // getNodeClusterRange takes a list of nodes
        if (node.nodeType !== Node.ELEMENT_NODE) {
            // TODO EGGMAIL NOW: change function purpose: create a range for all
            // inline blocks in a cluster
            cluster = this.getNodeClusterRange(node);
        }
        // if range, check commonAncestorContainer is contained in referenceDocument
        // -> determine exact way of checking if range or node (JS realm)
        // -> evaluate if it's best to be just before and just after the node instead of at
        // the start of it (is there a dimension difference for the boundingClientRect
        // -> maybe it's simpler to be before/after, then the logic to recover the first node is always
        // startcontainer + offset = node, instead of startcontainer being the node itself
        if (this.config.referenceDocument.contains(node)) {
            // Only the rect of a node inside the referenceDocument can be cached, as
            // the HTML and CSS content inside that document are fixed during conversion.
            const cachedRect =
                this.boundingClientRectsMap.get(this.dimensionsKey).get(cluster) ??
                new Proxy({}, this.cachedBoundingClientRectProxyHandler(cluster));
            this.boundingClientRectsMap.get(this.dimensionsKey).set(cluster, cachedRect);
            return cachedRect;
        }
        return new Proxy({}, this.cachedBoundingClientRectProxyHandler(cluster));
    }

    /**
     * Convenience function to get a single property value using the cache.
     * Prefer usage of `this.getComputedStyle` for elements outside of the
     * `reference` if multiple measures have to be made on the same element.
     */
    getStylePropertyValue(element, propertyName) {
        return this.getComputedStyle(element)[propertyName];
    }

    /**
     * @param {HtmlElement} element
     * @returns {Number} width
     */
    getStyleWidth(element) {
        return parseFloat(this.getStylePropertyValue(element, "width")) || 0;
    }

    /**
     * @param {HtmlElement} element
     * @returns {Number} height
     */
    getStyleHeight(element) {
        return parseFloat(this.getStylePropertyValue(element, "height")) || 0;
    }

    /**
     * Convenience function to get a single DOMRect value using the cache.
     * Prefer usage of `this.getBoundingClientRect` for elements outside of the
     * `reference` if multiple measures have to be made on the same element.
     */
    getRectValue(element, propertyName) {
        return this.getBoundingClientRect(element)[propertyName];
    }
}

registry
    .category("mail-html-conversion-plugins")
    .add(LayoutSnapshotCachePlugin.id, LayoutSnapshotCachePlugin);

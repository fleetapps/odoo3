// @odoo-module ignore
if (!Array.prototype.at) {
    Object.defineProperty(Array.prototype, "at", {
        enumerable: false,
        value: function (index) {
            if (index >= 0) {
                return this[index];
            }
            return this[this.length + index];
        },
    });
}

/**
 * Polyfill for Object.groupBy (Baseline 2024)
 */
if (!Object.groupBy) {
    Object.defineProperty(Object, "groupBy", {
        configurable: true,
        enumerable: false,
        writable: true,
        value: function (items, callbackfn) {
            const obj = Object.create(null);
            let i = 0;
            for (const item of items) {
                const key = callbackfn(item, i++);
                if (obj[key]) {
                    obj[key].push(item);
                } else {
                    obj[key] = [item];
                }
            }
            return obj;
        },
    });
}

/**
 * Polyfill for Map.groupBy (Baseline 2024)
 */
if (!Map.groupBy) {
    Object.defineProperty(Map, "groupBy", {
        configurable: true,
        enumerable: false,
        writable: true,
        value: function (items, callbackfn) {
            const map = new Map();
            let i = 0;
            for (const item of items) {
                const key = callbackfn(item, i++);
                if (map.has(key)) {
                    map.get(key).push(item);
                } else {
                    map.set(key, [item]);
                }
            }
            return map;
        },
    });
}

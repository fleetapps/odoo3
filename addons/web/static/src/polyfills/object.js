// @odoo-module ignore
if (!Object.hasOwn) {
    Object.hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
}
if (!Object.groupBy) {
    Object.defineProperty(Object, "groupBy", {
        enumerable: false,
        value:
            /**
             * @template T,K
             * @param {Iterable<T>} items
             * @param {(item: T) => K} callbackFn
             */
            function groupBy(items, callbackFn) {
                /** @type {Record<K, T[]>} */
                const groups = {};
                for (const element of items) {
                    const group = callbackFn(element);
                    if (!(group in groups)) {
                        groups[group] = [];
                    }
                    groups[group].push(element);
                }
                return groups;
            },
    });
}

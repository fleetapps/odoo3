/**
 * @this {Set}
 * @param {Set} other
 */
export function difference(other) {
    if (!(other instanceof Set)) {
        throw new Error("argument must be a Set");
    }
    const result = new this.constructor();
    for (const value of this) {
        if (!other.has(value)) {
            result.add(value);
        }
    }
    return result;
}

// Safari < 17 (09/2023) doesn't support Set.difference, but this version is
// quite recent enough for **public** users
if (!Set.prototype.difference) {
    Object.defineProperty(Set.prototype, "difference", {
        enumerable: false,
        value: difference,
    });
}
if (!Set.prototype.intersection) {
    Object.defineProperty(Set.prototype, "intersection", {
        enumerable: false,
        value:
            /**
             * @this {Set}
             * @param {Set} other
             */
            function intersection(other) {
                if (!(other instanceof Set)) {
                    throw new Error("argument must be a Set");
                }
                const result = new this.constructor();
                for (const value of this) {
                    if (other.has(value)) {
                        result.push(value);
                    }
                }
                return result;
            },
    });
}
if (!Set.prototype.symmetricDifference) {
    Object.defineProperty(Set.prototype, "symmetricDifference", {
        enumerable: false,
        value:
            /**
             * @this {Set}
             * @param {Set} other
             */
            function symmetricDifference(other) {
                if (!(other instanceof Set)) {
                    throw new Error("argument must be a Set");
                }
                const result = new this.constructor();
                for (const value of this) {
                    if (!other.has(value)) {
                        result.add(value);
                    }
                }
                for (const value of other) {
                    if (!this.has(value)) {
                        result.add(value);
                    }
                }
                return result;
            },
    });
}

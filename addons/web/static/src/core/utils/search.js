import { normalize } from "@web/core/l10n/utils";
import { isIterable } from "./arrays";

/**
 * This private function computes a score that represent the fact that the
 * string contains the pattern, or not
 *
 * - If the score is 0, the string does not contain the letters of the pattern in
 *   the correct order.
 * - if the score is > 0, it actually contains the letters.
 *
 * Better matches will get a higher score: consecutive letters are better,
 * and a match closer to the beginning of the string is also scored higher.
 *
 * @param {string} nPattern (normalized)
 * @param {string} nString (normalized)
 */
function getFuzzyScore(nPattern, nString) {
    let totalScore = 0;
    let currentScore = 0;
    let patternIndex = 0;

    const len = nString.length;

    for (let i = 0; i < len; i++) {
        if (nString[i] === nPattern[patternIndex]) {
            patternIndex++;
            currentScore += 100 + currentScore - i / 200;
        } else {
            currentScore = 0;
        }
        totalScore += currentScore;
    }

    return patternIndex === nPattern.length ? totalScore : 0;
}

/**
 * Return a list of things that matches a pattern, ordered by their 'score' (
 * higher score first). An higher score means that the match is better. For
 * example, consecutive letters are considered a better match.
 *
 * @template T
 * @param {string} pattern
 * @param {Iterable<T>} items
 * @param {(element: T) => (string | Iterable<string>)} mapFn
 * @returns {T[]}
 */
export function fuzzyLookup(pattern, items, mapFn) {
    const nPattern = normalize(pattern);
    /** @type {{ score: number, item: T }[]} */
    const results = [];
    for (const item of items) {
        let strings = mapFn(item);
        if (!isIterable(strings)) {
            strings = [strings];
        }
        let score = 0;
        for (const string of strings) {
            score = Math.max(score, getFuzzyScore(nPattern, normalize(string)));
        }
        if (score > 0) {
            results.push({ score, item });
        }
    }

    // Put best scores at the start of the list
    results.sort((a, b) => b.score - a.score);

    return results.map((r) => r.item);
}

// Does `pattern` fuzzy match `string`?
/**
 * @param {string} pattern
 * @param {string} string
 * @returns {boolean}
 */
export function fuzzyTest(pattern, string) {
    return getFuzzyScore(normalize(pattern), normalize(string)) > 0;
}

/**
 * Performs fuzzy matching using a Levenshtein distance algorithm
 * to find matches within an error margin between a pattern
 * and a list of words.
 *
 * If the pattern is found directly inside an item,
 * it's treated as a perfect match (score 0).
 * Otherwise, the `getScore` function calculates the distance
 * between the pattern and each candidate
 *
 * @param {string} pattern - The string to match.
 * @param {Iterable<string>} items - The list of strings to compare against the pattern.
 * @param {number} errorRatio - Controls how many errors can a word have depending of its length.
 * @returns {string[]} The list of the words that matches within a defined number of errors.
 */
export function fuzzyLevenshteinLookup(pattern, items, errorRatio = 3) {
    // We limit the maximum number of errors depending on the word length
    // to not have "overcorrections" into words that doesn't have anything
    // in common with what the user typed
    const maxNbrCorrection = Math.round(nPattern.length / errorRatio);
    const nPattern = normalize(pattern);
    /** @type {{ score: number, item: string }[]} */
    const results = [];
    for (const item of items) {
        const nCandidate = normalize(item);
        let score = -1;
        if (nCandidate.includes(nPattern)) {
            score = 0;
            results.push({ score, item: nPattern });
        } else {
            score = getLevenshteinScore(nPattern, nCandidate);
            if (score >= 0 && score <= maxNbrCorrection) {
                results.push({ score, item });
            }
        }
    }

    // Put lowest distances at the start of the list
    results.sort((a, b) => a.score - b.score);

    return results.map((r) => r.item);
}

/**
 * Computes the Levenshtein distance between two strings.
 *
 * @param {string} a
 * @param {string} b
 * @returns {number} The Levenshtein distance between `a` and `b`.
 */
function getLevenshteinScore(a, b) {
    const aLength = a.length;
    const bLength = b.length;

    const distanceMatrix = [];
    for (let i = 0; i <= aLength; i++) {
        distanceMatrix[i] = [];
        for (let j = 0; j <= bLength; j++) {
            distanceMatrix[i][j] = 0;
        }
    }

    for (let i = 0; i <= aLength; i++) {
        for (let j = 0; j <= bLength; j++) {
            if (Math.min(i, j) === 0) {
                distanceMatrix[i][j] = Math.max(i, j);
            } else {
                if (a[i - 1] === b[j - 1]) {
                    distanceMatrix[i][j] = distanceMatrix[i - 1][j - 1];
                } else {
                    distanceMatrix[i][j] = Math.min(
                        distanceMatrix[i - 1][j] + 1,
                        distanceMatrix[i][j - 1] + 1,
                        distanceMatrix[i - 1][j - 1] + 1
                    );
                }
            }
        }
    }
    return distanceMatrix[aLength][bLength];
}

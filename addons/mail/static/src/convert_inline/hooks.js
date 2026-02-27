import { onMounted, onWillUnmount, status, useComponent } from "@odoo/owl";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { getCSSRules, toInline } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { loadIframeBundles, loadIframe } from "@mail/convert_inline/iframe_utils";
import { Mutex } from "@web/core/utils/concurrency";

export const EMAIL_DESKTOP_DIMENSIONS = {
    width: 1320,
    height: 1000,
};
export const EMAIL_MOBILE_DIMENSIONS = {
    width: 360,
    height: 1000,
};

/**
 * Hook to handle email HTML conversion in a mail HtmlField.
 * @param {Object} targetRef ref-like object with `el` property, container for
 *                 the iframe where the conversion will happen
 * @param {Array<string>} [options.bundles] bundles to load for the conversion
 * @returns {Object}
 */
export function useEmailHtmlConverter({ targetRef, bundles = [] }) {
    let reference, referenceDocument; // Element and Document in which the conversion takes place.
    let currentConfig = {};
    const keepAlivePromises = new Set();
    const conversionMutex = new Mutex();
    const cmp = useComponent();
    const referenceIframe = renderToElement("mail.EmailHtmlConverterReferenceIframe", {
        isBrowserSafari,
    });
    const updateLayoutDimensions = ({ width, height } = EMAIL_DESKTOP_DIMENSIONS) => {
        referenceIframe.style.setProperty("max-width", `${width}px`, "important");
        referenceIframe.style.setProperty("min-width", `${width}px`, "important");
        referenceIframe.style.setProperty("min-height", `${height}px`, "important");
    };
    const cleanupEmailHtmlConversion = () => {
        if (reference?.isConnected) {
            reference.remove();
            reference = undefined;
        }
    };
    const prepareEmailHtmlConversion = async (fragment) => {
        await iframeLoaded;
        cleanupEmailHtmlConversion();
        reference = renderToElement("mail.EmailHtmlConverterReference");
        reference.append(fragment);
        referenceDocument.body.append(reference);
    };
    const getCurrentConfig = (newConfig) => {
        if (newConfig) {
            currentConfig = newConfig;
        }
        return {
            ...currentConfig,
            reference,
            referenceDocument,
        };
    };

    const assetsPromise = loadIframeBundles(referenceIframe, bundles);
    const contentPromise = loadIframe(referenceIframe, () => {
        referenceDocument = referenceIframe.contentDocument;
        referenceDocument.head.append(renderToFragment("mail.EmailHtmlConverterHead"));
        // The iframe body must exactly have the iframe horizontal dimensions.
        referenceDocument.body.setAttribute(
            "style",
            `margin: 0 !important;
            padding: 0 !important;`
        );
    });
    const iframeLoaded = Promise.all([contentPromise, assetsPromise]);
    iframeLoaded.catch((error) => {
        if (status(cmp) === "destroyed") {
            // Ignore loading errors if the Component was destroyed, since the
            // iframe was removed, there is nothing to load for.
            return;
        }
        throw error;
    });

    onMounted(() => {
        targetRef.el.append(referenceIframe);
    });
    onWillUnmount(() =>
        // Lazily cleanup the computation iframe, to try and finish the work
        // if possible.
        Promise.allSettled([...keepAlivePromises, conversionMutex.getUnlockedDef()]).then(() => {
            cleanupEmailHtmlConversion();
            referenceIframe.remove();
        })
    );
    const convertToEmailHtml = async (fragment, config) => {
        await prepareEmailHtmlConversion(fragment);
        updateLayoutDimensions();
        config = getCurrentConfig(config);
        for (const cb of config.preProcessCallbacks ?? []) {
            cb(config.reference);
        }
        const cssRules = getCSSRules(config.referenceDocument);
        await toInline(config.reference, cssRules);
        cleanupEmailHtmlConversion();
        return config.reference.innerHTML;
    };
    const keepAlive = (promise) => {
        keepAlivePromises.add(promise);
        return promise.then(
            () => keepAlivePromises.delete(promise),
            () => keepAlivePromises.delete(promise)
        );
    };
    return {
        /**
         * @param {DocumentFragment} fragment reference content to convert as
         *        mail compliant HTML.
         * @param {Object} [config]
         * @returns {Promise<string>} mail compliant HTML.
         */
        convertToEmailHtml: (fragment, config) =>
            conversionMutex.exec(() => convertToEmailHtml(fragment, config)),
        /**
         * @returns {Promise<void>} resolved as soon as the last conversion is
         *          completed (directly if there is no ongoing conversion)
         */
        getUnlockedDef: () => conversionMutex.getUnlockedDef(),
        /**
         * @param {Promise} promise keep this converter alive until the given
         *        promise is settled.
         * @returns {Promise<void>} resolved when the given promise is settled.
         */
        keepAlive,
        /**
         * @param {Object} dimensions
         * @param {Number} dimensions.width
         * @param {Number} dimensions.height
         */
        updateLayoutDimensions,
    };
}

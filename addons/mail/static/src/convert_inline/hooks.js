import { onMounted, onWillUnmount, status, useComponent } from "@odoo/owl";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { EmailHtmlConverter } from "@mail/convert_inline/email_html_converter";
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
export function useEmailHtmlConverter({ Plugins, bundles, targetRef, isVisible }) {
    let converter, reference, referenceDocument; // Element and Document in which the conversion takes place.
    let currentConfig = {};
    const keepAlivePromises = new Set();
    const conversionMutex = new Mutex();
    const cmp = useComponent();
    const referenceIframe = renderToElement("mail.EmailHtmlConverterReferenceIframe", {
        isBrowserSafari,
        isVisible,
    });
    const updateLayoutDimensions = ({ width, height } = EMAIL_DESKTOP_DIMENSIONS) => {
        referenceIframe.style.setProperty("max-width", `${width}px`, "important");
        referenceIframe.style.setProperty("min-width", `${width}px`, "important");
        referenceIframe.style.setProperty("min-height", `${height}px`, "important");
        if (converter) {
            converter.onLayoutDimensionsUpdate({ width, height });
        }
    };
    const cleanupEmailHtmlConversion = () => {
        if (reference?.isConnected) {
            reference.remove();
            reference = undefined;
        }
        if (converter) {
            converter.destroy();
            converter = undefined;
        }
    };
    const prepareEmailHtmlConversion = async (fragment) => {
        await iframeLoaded;
        cleanupEmailHtmlConversion();
        converter = new EmailHtmlConverter(undefined, cmp.env.services);
        reference = renderToElement("mail.EmailHtmlConverterReference");
        reference.append(fragment);
        referenceDocument.body.append(reference);
    };
    const getCurrentConfig = (newConfig) => {
        if (newConfig) {
            currentConfig = newConfig;
        }
        return {
            Plugins: Plugins ?? registry.category("mail-html-conversion-plugins").getAll(),
            ...currentConfig,
            reference,
            referenceDocument,
            updateLayoutDimensions,
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
        const htmlConverted = converter.convertToEmailHtml(getCurrentConfig(config));
        if (!isVisible) {
            return htmlConverted.then((emailHtml) => {
                cleanupEmailHtmlConversion();
                return emailHtml;
            });
        }
        return htmlConverted;
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

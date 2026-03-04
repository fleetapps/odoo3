// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

let globalAssetCaches;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Browser module needs to be mocked to patch the `location` global object since
 * it can't be directly mocked on the window object.
 *
 * @param {string} name
 * @param {OdooModuleFactory} factory
 */
export function mockAssetsFactory(name, { fn }) {
    return function mockAssets(...args) {
        const assetsModule = fn(...args);

        if (globalAssetCaches) {
            Object.assign(assetsModule.assetCaches, globalAssetCaches);
        } else {
            globalAssetCaches = assetsModule.assetCaches;
        }

        return assetsModule;
    };
}

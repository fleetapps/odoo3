declare module "services" {
    import { translateUiServiceFactory } from "@web/core/debug/translate_ui_service";

    export interface translate_ui {
        translate_ui: typeof translateUiServiceFactory;
    }
}

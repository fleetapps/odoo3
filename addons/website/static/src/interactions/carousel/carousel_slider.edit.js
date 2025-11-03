import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";
import { registry } from "@web/core/registry";

const CarouselSliderEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            _root: {
                ...this.dynamicContent._root,
                "t-on-content_changed": this.onContentChanged,
            },
        };
        // Pause carousel in edit mode.
        carouselOptions = { ride: false, pause: true, keyboard: false };
        showClickableSlideLinks = false;

        start() {
            super.start();
            // Recompute carousel height when its class changes (e.g., when a
            // custom snippet sets `o_full_screen_height` and later switches the
            // carousel height to `auto`) to ensure the correct min-height is
            // reapplied to carousel items.
            this.carouselClassObserver = new MutationObserver(() => {
                this.computeMaxHeight();
            });
            this.carouselClassObserver.observe(this.el.closest("section"), {
                attributes: true,
                attributeFilter: ["class"],
            });
            this.registerCleanup(() => this.carouselClassObserver?.disconnect());
        }
        onContentChanged() {
            this.computeMaxHeight();
        }
    };

registry.category("public.interactions.edit").add("website.carousel_slider", {
    Interaction: CarouselSlider,
    mixin: CarouselSliderEdit,
});

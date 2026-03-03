import { registry } from "@web/core/registry";
import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";
import { EventsMixin } from "./events_mixin";

const EventsCarouselBase = EventsMixin(DynamicSnippetCarousel);

export class DynamicSnippetCarouselEvents extends EventsCarouselBase {
    static selector = ".s_events_carousel";
}

registry
    .category("public.interactions")
    .add("website_event.event_carousel", DynamicSnippetCarouselEvents);

registry.category("public.interactions.edit").add("website_event.event_carousel_base", {
    Interaction: EventsCarouselBase,
});

registry.category("public.interactions.edit").add("website_event.event_carousel", {
    Interaction: DynamicSnippetCarouselEvents,
});

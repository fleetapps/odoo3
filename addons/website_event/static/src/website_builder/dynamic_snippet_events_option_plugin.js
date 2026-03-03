import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { DYNAMIC_SNIPPET_CAROUSEL } from "@website/builder/plugins/options/dynamic_snippet_carousel_option_plugin";
import {
    DYNAMIC_SNIPPET,
    setDatasetIfUndefined,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { DynamicSnippetCarouselEventsOption } from "./dynamic_snippet_carousel_events_option";
import { DynamicSnippetEventsOption } from "./dynamic_snippet_events_option";

class DynamicSnippetEventsOptionPlugin extends Plugin {
    static id = "dynamicSnippetEventsOption";
    static dependencies = ["dynamicSnippetOption", "dynamicSnippetCarouselOption"];
    static shared = ["getModelNameFilter"];
    static eventSelector = [
        `${DynamicSnippetEventsOption.selector}, ${DynamicSnippetCarouselEventsOption.selector}`,
    ];
    modelNameFilter = "event.event";
    resources = {
        builder_options: [
            withSequence(DYNAMIC_SNIPPET, DynamicSnippetEventsOption),
            withSequence(DYNAMIC_SNIPPET_CAROUSEL, DynamicSnippetCarouselEventsOption),
        ],
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(DynamicSnippetEventsOptionPlugin.eventSelector)) {
            setDatasetIfUndefined(snippetEl, "numberOfRecords", 3);
            if (snippetEl.matches(DynamicSnippetEventsOption.selector)) {
                await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                    snippetEl,
                    this.modelNameFilter
                );
            } else {
                await this.dependencies.dynamicSnippetCarouselOption.setOptionsDefaultValues(
                    snippetEl,
                    this.modelNameFilter
                );
            }
        }
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetEventsOptionPlugin.id, DynamicSnippetEventsOptionPlugin);

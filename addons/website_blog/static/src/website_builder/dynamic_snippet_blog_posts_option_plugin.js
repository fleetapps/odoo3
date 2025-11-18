import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { DYNAMIC_SNIPPET_CAROUSEL } from "@website/builder/plugins/options/dynamic_snippet_carousel_option_plugin";
import {
    DYNAMIC_SNIPPET,
    setDatasetIfUndefined,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { DynamicSnippetBlogPostsOption } from "./dynamic_snippet_blog_posts_option";
import { DynamicSnippetBlogPostsCarouselOption } from "./dynamic_snippet_blog_posts_carousel_option";

/**
 * @typedef { Object } DynamicSnippetBlogPostsOptionShared
 * @property { DynamicSnippetBlogPostsOptionPlugin['fetchBlogs'] } fetchBlogs
 * @property { DynamicSnippetBlogPostsOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

class DynamicSnippetBlogPostsOptionPlugin extends Plugin {
    static id = "dynamicSnippetBlogPostsOption";
    static dependencies = ["dynamicSnippetOption", "dynamicSnippetCarouselOption"];
    static shared = ["fetchBlogs", "getModelNameFilter"];
    static blogSelector = [
        `${DynamicSnippetBlogPostsOption.selector}, ${DynamicSnippetBlogPostsCarouselOption.selector}`,
    ];
    modelNameFilter = "blog.post";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            withSequence(DYNAMIC_SNIPPET, DynamicSnippetBlogPostsOption),
            withSequence(DYNAMIC_SNIPPET_CAROUSEL, DynamicSnippetBlogPostsCarouselOption),
        ],
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    setup() {
        this.blogs = undefined;
    }
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(DynamicSnippetBlogPostsOptionPlugin.blogSelector)) {
            setDatasetIfUndefined(snippetEl, "filterByBlogId", -1);
            if (snippetEl.matches(DynamicSnippetBlogPostsOption.selector)) {
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
    async fetchBlogs() {
        if (!this.blogs) {
            this.blogs = this._fetchBlogs();
        }
        return this.blogs;
    }
    async _fetchBlogs() {
        // TODO put in an utility function
        const websiteDomain = [
            "|",
            ["website_id", "=", false],
            ["website_id", "=", this.services.website.currentWebsite.id],
        ];
        return this.services.orm.searchRead("blog.blog", websiteDomain, ["id", "name"]);
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetBlogPostsOptionPlugin.id, DynamicSnippetBlogPostsOptionPlugin);

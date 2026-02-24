import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class BlogPostPageOption extends BaseOptionComponent {
    static template = "website_blog.blogPostPageOption";
    static selector = "main:has(#o_wblog_index_content)";
    static title = _t("Blogs Design");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;

    setup() {
        super.setup();
        this.state = useDomState((el) => ({
            isOnBlogPage: !!el.querySelector('.o_wblog_homepage_top'),
        }));
    }
}

export class BlogPostPageOptionPlugin extends Plugin {
    static id = "blogPostPageOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [BlogPostPageOption],
        blog_post_design_list_to_save: {
            selector: "#o_wblog_index_content",
            getData(el) {
                const blogPostOptClasses = Array.from(el.classList).filter((className) =>
                    className.startsWith("o_wblog_post_opt_")
                );
                const updateData = {
                    blog_post_opt_blog_page_container: blogPostOptClasses.join(" "),
                };
                return updateData;
            },
        },
    };
}

registry.category("website-plugins").add(BlogPostPageOptionPlugin.id, BlogPostPageOptionPlugin);

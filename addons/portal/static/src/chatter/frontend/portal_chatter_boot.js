import { loadBundle } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { Interaction } from "@web/public/interaction";
import { session } from "@web/session";

odoo.portalChatterReady = Promise.withResolvers();

const loadChatter = memoize(() => loadBundle("portal.assets_chatter"));

export class PortalChatterBoot extends Interaction {
    static selector = ".o_portal_chatter";

    async willStart() {
        const root = document.createElement("div");
        root.setAttribute("id", "chatterRoot");
        if (this.dataset.two_columns === "true") {
            root.classList.add("p-0");
        }
        this.el.appendChild(root);
        await loadChatter();
        this.shadowRoot = root.attachShadow({ mode: "open" });
        const { loadCssFromBundle } = odoo.loader.modules.get("@mail/utils/common/misc");
        await loadCssFromBundle(this.shadowRoot, "portal.assets_chatter_style");
    }

    start() {
        this.initChatter();
    }

    get dataset() {
        return this.el.dataset;
    }

    async initChatter() {
        const { PortalChatter } = odoo.loader.modules.get("@portal/chatter/portal/portal_chatter");
        const dataset = this.dataset;
        const props = {
            composer: !!(parseInt(dataset.allow_composer) && (dataset.token || !session.is_public)),
            displayRating: dataset.display_rating === "True",
            resId: parseInt(dataset.res_id),
            resModel: dataset.res_model,
            twoColumns: dataset.two_columns === "true",
        };
        this.mountComponent(this.shadowRoot, PortalChatter, props);
        const store = this.env.services["mail.store"];
        const thread = store["mail.thread"].insert({
            access_token: dataset.token,
            hash: dataset.hash,
            id: dataset.res_id,
            model: dataset.res_model,
            pid: parseInt(dataset.pid),
        });
        store.insert(
            await rpc(
                "/portal/chatter_init",
                {
                    thread_model: thread.model,
                    thread_id: thread.id,
                    ...thread.rpcParams,
                },
                { silent: true }
            )
        );
        odoo.portalChatterReady.resolve(true);
    }
}

registry.category("public.interactions").add("portal.chatter.boot", PortalChatterBoot);

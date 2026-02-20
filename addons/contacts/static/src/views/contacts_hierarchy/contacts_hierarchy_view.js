import { registry } from "@web/core/registry";
import { hierarchyView } from "@web_hierarchy/hierarchy_view";
import { ContactsHierarchyRenderer } from "./contacts_hierarchy_renderer";

export const ContactsHierarchyView = {
    ...hierarchyView,
    Renderer: ContactsHierarchyRenderer,
};

registry.category("views").add("contacts_hierarchy", ContactsHierarchyView);

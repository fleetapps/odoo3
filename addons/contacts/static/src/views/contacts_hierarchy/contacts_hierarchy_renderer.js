import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { HierarchyRenderer } from "@web_hierarchy/hierarchy_renderer";
import { ContactsHierarchyCard } from "./contacts_hierarchy_card";

export class ContactsHierarchyRenderer extends HierarchyRenderer {
    static template = "contacts.ContactsHierarchyRenderer";
    static components = {
        ...HierarchyRenderer.components,
        HierarchyCard: ContactsHierarchyCard,
        Avatar,
    };

}

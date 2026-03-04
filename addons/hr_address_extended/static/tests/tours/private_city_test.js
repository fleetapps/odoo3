import { registry } from '@web/core/registry';

registry.category("web_tour.tours").add("private_city_test", {
    url: "/odoo",
    steps: () => [
    {
        "trigger": ".o_app[data-menu-xmlid='hr\\.menu_hr_root']",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o_kanban_record:nth-child(1) img",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o_notebook_headers button[name='personal_information']",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o_field_widget[name='private_country_id'] .o-autocomplete--input",
        "run": "edit unite",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o-autocomplete--dropdown-item:nth-child(3) > a",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o_field_widget[name='private_state_id'] .o-autocomplete--input",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o-autocomplete--dropdown-item:nth-child(3) > a",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o_field_widget[name='private_city_id'] .o-autocomplete--input",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o-autocomplete--dropdown-item:nth-child(4) > a",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o_form_button_save",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o_field_widget[name='private_state_id'] .o-autocomplete--input",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o-autocomplete--dropdown-item:nth-child(4) > a",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o_field_widget[name='private_city_id'] .o-autocomplete--input",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o-autocomplete--dropdown-item:nth-child(5) > a",
        "run": "click",
        "tooltipPosition": "bottom"
    },
    {
        "trigger": ".o_form_button_save",
        "run": "click",
        "tooltipPosition": "bottom"
    }
]
})
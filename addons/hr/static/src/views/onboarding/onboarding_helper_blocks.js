import { Component } from "@odoo/owl";

class OnboardingIconCard extends Component {
    static template = "hr.OnboardingIconCard";
    static props = {
        label: { type: String },
        iconPath: { type: String },
    };
}

export class OnboardingHelperBlocks extends Component {
    static template = "hr.OnboardingHelperBlocks";
    static components = { OnboardingIconCard };
    static props = {};
}

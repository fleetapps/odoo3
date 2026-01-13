import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

export class ImageAndFaOption extends BaseOptionComponent {
    static template = "html_builder.ImageAndFaOption";
    static selector = "span.fa, i.fa, img";
    static name = "imageAndFaOption";
    static components = { BorderConfigurator };
}

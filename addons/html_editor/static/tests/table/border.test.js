import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor } from "../_helpers/editor";
import { expandToolbar } from "../_helpers/toolbar";

test("should apply border color", async () => {
    await setupEditor(
        `<table class="o_selected_table"><tbody><tr>
            <td class="o_selected_td">11[]</td>
        </tr></tbody></table>`,
        {
            // Force a predefined color because they can be different.
            styleContent: ":root { --600: #7E57C0; }",
        }
    );
    await expandToolbar();
    await contains(".btn:has(.fa-pencil)").click();
    await contains("[data-color='600']").click();
    expect("table").toHaveStyle({ "--table-cell-border-color": "#7E57C0" });
});

test("should apply border width", async () => {
    await setupEditor(`
        <table class="o_selected_table"><tbody><tr>
            <td class="o_selected_td">11[]</td>
        </tr></tbody></table>`);
    await expandToolbar();
    await contains(".btn[name='table_border_width']").click();
    await contains("button:has(.o-border-preview[style*='border-width: 3px'])").click();
    expect("table").toHaveStyle({ "--table-cell-border-width": "3px" });
});

test("should apply border style", async () => {
    await setupEditor(`
        <table class="o_selected_table"><tbody><tr>
            <td class="o_selected_td">11[]</td>
        </tr></tbody></table>`);
    await expandToolbar();
    await contains(".btn[name='table_border_style']").click();
    await contains("button:has(.o-border-preview[style*='border-style: dotted'])").click();
    expect("table").toHaveStyle({ "--table-cell-border-style": "dotted" });
});

test("should remove all border specification on color delete", async () => {
    await setupEditor(`
        <table class="o_selected_table o_table_border_styled" style="--table-cell-border-color: #FF9C00; --table-cell-border-width: 1px; --table-cell-border-style: solid;"><tbody><tr>
            <td class="o_selected_td">11[]</td>
        </tr></tbody></table>`);
    await expandToolbar();
    await contains(".btn:has(.fa-pencil)").click();
    await contains(".o_font_color_selector .fa-trash").click();
    expect("table").not.toHaveStyle("--table-cell-border-color");
    expect("table").not.toHaveStyle("--table-cell-border-width");
    expect("table").not.toHaveStyle("--table-cell-border-style");
    expect("table").not.toHaveClass("o_table_border_styled");
});

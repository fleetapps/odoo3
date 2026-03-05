import { reactive } from "@web/owl2/utils";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { ColorSelector } from "@html_editor/main/font/color_selector";
import { TableBorderStyleSelector } from "./table_border_style_selector";
import { TableBorderWidthSelector } from "./table_border_width_selector";

const borderStyleItems = [
    {
        value: "solid",
    },
    {
        value: "dashed",
    },
    {
        value: "dotted",
    },
    {
        value: "double",
    },
];

const borderWidthItems = [
    {
        value: "1px",
        margin: "5px",
    },
    {
        value: "2px",
        margin: "6px",
    },
    {
        value: "3px",
        margin: "6px",
    },
    {
        value: "4px",
        margin: "7px",
    },
    {
        value: "5px",
        margin: "7px",
    },
];

export class TableBorderPlugin extends Plugin {
    static id = "tableBorder";
    static dependencies = ["colorUi", "history", "selection"];
    static shared = ["applyBorder", "getBorder"];

    /** @type {import("plugins").EditorResources} */
    resources = {
        toolbar_items: [
            withSequence(10, {
                id: "table_border_color",
                groupId: "table",
                description: _t("Table border color"),
                isAvailable: () =>
                    this.dependencies.selection
                        .getTargetedNodes()
                        .some((node) => closestElement(node, "td, th")),
                Component: ColorSelector,
                props: {
                    ...this.dependencies.colorUi.getPropsForColorSelector("foreground"),
                    type: "custom",
                    customIconClass: "fa-pencil",
                    enabledTabs: ["solid", "custom"],
                    colorPrefix: "--",
                    getSelectedColors: () => {
                        const table = this.dependencies.selection
                            .getTargetedNodes()
                            .map((node) => closestElement(node, "table"))[0];
                        this.selectedBorderColors.color = this.getBorder(table, "color");
                        return this.selectedBorderColors;
                    },
                    applyColor: (color) => this.applyBorderCommit("color", color),
                    applyColorPreview: (color) => this.applyBorderPreview("color", color),
                    applyColorResetPreview: this.applyBorderResetPreview.bind(this),
                    onClose: () => this.dependencies.selection.focusEditable(),
                    getTargetedElements: () => {
                        const nodes = this.dependencies.selection.getTargetedNodes();
                        return nodes.map((node) => closestElement("table"));
                    },
                },
            }),
            withSequence(11, {
                id: "table_border_width",
                groupId: "table",
                description: _t("Table border width"),
                isAvailable: () =>
                    this.dependencies.selection
                        .getTargetedNodes()
                        .some((node) => closestElement(node, "td, th")),
                Component: TableBorderWidthSelector,
                props: {
                    getItems: () => borderWidthItems,
                    getDisplay: () => {
                        const table = this.dependencies.selection
                            .getTargetedNodes()
                            .map((node) => closestElement(node, "table"))[0];
                        this.selectedBorderWidth.displayName = this.getBorder(table, "width");
                        return this.selectedBorderWidth;
                    },
                    onSelected: (item) => {
                        this.applyBorderCommit("width", item.value);
                        this.selectedBorderWidth.displayName = item.value;
                    },
                },
            }),
            withSequence(12, {
                id: "table_border_style",
                groupId: "table",
                description: _t("Table border style"),
                isAvailable: () =>
                    this.dependencies.selection
                        .getTargetedNodes()
                        .some((node) => closestElement(node, "td, th")),
                Component: TableBorderStyleSelector,
                props: {
                    getItems: () => borderStyleItems,
                    getDisplay: () => {
                        const table = this.dependencies.selection
                            .getTargetedNodes()
                            .map((node) => closestElement(node, "table"))[0];
                        this.selectedBorderStyle.displayName = this.getBorder(table, "style");
                        return this.selectedBorderStyle;
                    },
                    onSelected: (item) => {
                        this.applyBorderCommit("style", item.value);
                        this.selectedBorderStyle.displayName = item.value;
                    },
                },
            }),
        ],
    };

    setup() {
        // Background color is required by the color picker.
        this.selectedBorderColors = reactive({ color: "", backgroundColor: "" });
        this.selectedBorderWidth = reactive({ displayName: "1px" });
        this.selectedBorderStyle = reactive({ displayName: "solid" });
        this.previewableApplyBorder = this.dependencies.history.makePreviewableOperation(
            (prop, value) => this.applyBorder(prop, value)
        );
    }

    /**
     * Returns the current value of a border property for a table.
     *
     * @param {HTMLTableElement} table
     * @param {string} subProperty color, width or style
     */
    getBorder(table, subProperty) {
        const cellStyle = getComputedStyle(table.querySelector("td"));
        let result = cellStyle.getPropertyValue(`border-${subProperty}`);
        // Handle defaults
        switch (subProperty) {
            case "width":
                if (result === "0px") {
                    result = "1px";
                }
                break;
            case "style":
                if (result === "none") {
                    result = "solid";
                }
                break;
        }
        return result;
    }

    /**
     * Applies a border property value on tables of the current selection.
     *
     * @param {string} subProperty color, width or style
     * @param {string} value
     */
    applyBorder(subProperty, value) {
        const tables = new Set(
            this.dependencies.selection
                .getTargetedNodes()
                .map((node) => closestElement(node, "table"))
        );
        if (value === "") {
            for (const table of tables) {
                table.classList.remove("o_table_border_styled");
                for (const prop of ["color", "width", "style"]) {
                    table.style.removeProperty(`--table-cell-border-${prop}`);
                }
            }
            return;
        }
        if (subProperty === "color" && value.startsWith("--")) {
            const htmlStyle = getHtmlStyle(this.document);
            value = getCSSVariableValue(value.substring(2), htmlStyle);
        }
        for (const table of tables) {
            if (!table.classList.contains("o_table_border_styled")) {
                table.classList.add("o_table_border_styled");
                for (const prop of ["color", "width", "style"]) {
                    table.style.setProperty(
                        `--table-cell-border-${prop}`,
                        this.getBorder(table, prop)
                    );
                }
            }
            table.style.setProperty(`--table-cell-border-${subProperty}`, value);
        }
    }

    /**
     * Apply border on the current selected tables.
     *
     * @param {string} subProperty color, width or style
     * @param {string} value
     */
    applyBorderCommit(subProperty, value) {
        this.previewableApplyBorder.commit(subProperty, value);
        if (subProperty === "color" && value.startsWith("--")) {
            const htmlStyle = getHtmlStyle(this.document);
            value = getCSSVariableValue(value.substring(2), htmlStyle);
        }
        this.selectedBorderColors.color = value;
    }
    /**
     * Apply border on the current selected tables in preview mode so that it can be reset.
     *
     * @param {string} subProperty color, width or style
     * @param {string} value
     */
    applyBorderPreview(subProperty, value) {
        // Preview the border before applying it.
        this.previewableApplyBorder.preview(subProperty, value, true);
    }
    /**
     * Reset the border applied in preview mode.
     */
    applyBorderResetPreview() {
        this.previewableApplyBorder.revert();
    }
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Command


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Section-related fields
    is_optional = fields.Boolean(
        string="Optional Line",
        copy=True,
        default=False,
    )  # Whether this section's lines are optional in the portal.

    # === COMPUTE METHODS === #

    @api.depends('product_id')
    def _compute_name(self):
        # Take the description on the order template if the product is present in it
        super()._compute_name()
        for line in self:
            if line.product_id and line.order_id.sale_order_template_id and line._use_template_name():
                for template_line in line.order_id.sale_order_template_id.sale_order_template_line_ids:
                    if line.product_id == template_line.product_id and template_line.name:
                        # If a specific description was set on the template, use it
                        # Otherwise the description is handled by the super call
                        lang = line.order_id.partner_id.lang
                        line.name = template_line.with_context(lang=lang).name + line.with_context(lang=lang)._get_sale_order_line_multiline_description_variants()
                        break

    def _use_template_name(self):
        """ Allows overriding to avoid using the template lines descriptions for the sale order lines descriptions.
    This is typically useful for 'configured' products, such as event_ticket or event_booth, where we need to have
    specific configuration information inside description instead of the default values.
    """
        self.ensure_one()
        return True

    # === TOOLING ===#

    def _is_line_optional(self):
        """ Returns whether the line is optional or not.

        A line is optional if it is directly under an optional (sub)section, or under a subsection
        which is itself under an optional section.
        """
        self.ensure_one()
        return (
            self.parent_id.is_optional
            or (
                self.parent_id.display_type == 'line_subsection'
                and self.parent_id.parent_id.is_optional
            )
        )

    def _can_be_edited_on_portal(self):
        return super()._can_be_edited_on_portal() and self._is_line_optional()

    def _prepare_template_line_values(self):
        """Prepare create values for a sale order template line from a sale order line.

        If the line is linked to a product, the product is stored and pricing
        is recomputed later. For product lines without a product, price, discount, and taxes
        are copied explicitly.

        :return: `sale.order.template.line` create values
        :rtype: dict
        """
        self.ensure_one()
        vals = {
            'name': self.name,
            'product_uom_qty': self.product_uom_qty,
            'product_uom_id': self.product_uom_id.id,
            'display_type': self.display_type,
            'is_optional': self.is_optional,
            'collapse_composition': self.collapse_composition,
            'collapse_prices': self.collapse_prices,
        }

        if not self.product_id and not self.display_type:
            vals.update({
                'tax_ids': self.tax_ids.ids,
                'discount': self.discount,
                'price_unit': self.price_unit,
            })
        else:
            vals['product_id'] = self.product_id.id

        return vals

    # === PUBLIC === #

    @api.model
    def save_section_template(self, line_id):
        """Create a `sale.order.template` from a section and its related lines.

        Given a section line of a sale order, this method collects the section
        itself and all its related lines, and stores them as an inactive
        ``sale.order.template`` marked as a section template. If a template with
        the same name and source sale order already exists, its lines are replaced;
        otherwise, a new template is created.

        :param int line_id: ID of the section sale order line used as template root
        :return: None
        """
        line = self.browse(line_id)
        section_lines = line._get_section_lines()

        exisiting_template = self.env['sale.order.template'].with_context(active_test=False).search([
            ('name', '=', line.name),
            ('source_order_id', '=', line.order_id.id),
            ('user_id', '=', self.env.user.id),
            ('is_section_template', '=', True),
        ])

        if exisiting_template:
            template_lines_data = [Command.clear()]
            template_lines_data += [
                Command.create(section_line._prepare_template_line_values())
                for section_line in line + section_lines
            ]
            exisiting_template.sale_order_template_line_ids = template_lines_data
        else:
            self.env['sale.order.template'].create({
                'name': line.name,
                'source_order_id': line.order_id.id,
                'is_section_template': True,
                'active': False,
                'sale_order_template_line_ids': [
                    Command.create(section_line._prepare_template_line_values())
                    for section_line in line + section_lines
                ],
            })

    @api.model
    def prepare_section_template_order_lines(self, template_id, order_changes, fields_spec):
        """Prepare `sale.order.line` value dicts from a section template.

        Builds order line values from the given section template, applies
        `sale.order.line` onchange with provided order-level changes, and
        returns the resulting values ready for insertion.

        :param int template_id: ID of the section sale order template
        :param dict order_changes: Order values to consider fro onchange
        :param dict fields_spec: Fields specification for onchange
        :return: Prepared sale order line values
        :rtype: list[dict]
        """
        section_template = self.env['sale.order.template'].browse(template_id)
        result = []

        for line in section_template.sale_order_template_line_ids:
            onchange_values = {**line._prepare_order_line_values(), **order_changes}
            onchange_result = self.env['sale.order.line'].onchange(
                onchange_values,
                [],
                fields_spec,
            )
            result.append(onchange_result.get('value', {}))

        return result

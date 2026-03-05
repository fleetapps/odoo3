# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report


def _post_init_hook(env):
    terms_conditions = env['ir.config_parameter'].get_bool('account.use_invoice_terms')
    if not terms_conditions:
        env['ir.config_parameter'].set_bool('account.use_invoice_terms', True)
    companies = env['res.company'].search([])
    for company in companies:
        company.terms_type = 'html'
    env['website'].search([]).auth_signup_uninvited = 'b2c'

    existing_websites = env['website'].search([])
    for website in existing_websites:
        website._create_checkout_steps()
    _create_extra_variant_images(env)

def uninstall_hook(env):
    ''' Need to reenable the `product` pricelist multi-company rule that were
        disabled to be 'overridden' for multi-website purpose
    '''
    pl_rule = env.ref('product.product_pricelist_comp_rule', raise_if_not_found=False)
    pl_item_rule = env.ref('product.product_pricelist_item_comp_rule', raise_if_not_found=False)
    multi_company_rules = pl_rule or env['ir.rule']
    multi_company_rules += pl_item_rule or env['ir.rule']
    multi_company_rules.write({'active': True})


def _create_extra_variant_images(env):
    templates = env['product.template'].search([
        ('image_1920', '!=', False)
    ])

    image_vals = []

    for template in templates:
        existing_binaries = template.product_template_image_ids.mapped('image_1920')

        if template.image_1920 and template.image_1920 not in existing_binaries:
            image_vals.append({
                'name': template.display_name,
                'product_tmpl_id': template.id,
                'image_1920': template.image_1920,
                'sequence': 0,
            })
            existing_binaries.append(template.image_1920)

        for product in template.product_variant_ids:
            variant_image = product.image_variant_1920

            if (
                variant_image
                and variant_image != template.image_1920
                and variant_image not in existing_binaries
            ):
                image_vals.append({
                    'name': product.display_name,
                    'product_tmpl_id': template.id,
                    'attribute_value_ids': [(6, 0, product.product_template_attribute_value_ids.ids)],
                    'image_1920': variant_image,
                    'sequence': 0,
                })
                existing_binaries.append(variant_image)

    if image_vals:
        env['product.image'].create(image_vals)

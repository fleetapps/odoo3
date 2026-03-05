# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo.tests import tagged

from odoo.tests.common import HttpCase
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged('post_install', '-at_install')
class TestClickAndCollectFlow(HttpCase, ClickAndCollectCommon):

    def test_click_and_collect_widget_as_public_user(self):
        self.storable_product.name = "Test CAC Product"
        self.provider.write(
            {
                'state': 'enabled',
                'is_published': True,
            }
        )
        self.in_store_dm.warehouse_ids[0].partner_id = self.env['res.partner'].create(
            {
                **self.dummy_partner_address_values,
                'name': "Shop 1",
                'partner_latitude': 1.0,
                'partner_longitude': 2.0,
            }
        )
        self.start_tour('/', 'website_sale_collect_widget')

    def test_click_and_collect_excluded_tag(self):
        excluded_tag = self.env["product.tag"].create({"name": "Multiple Products"})
        self.in_store_dm.excluded_tag_ids = excluded_tag
        self.storable_product.all_product_tag_ids = excluded_tag
        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            combination_info = self.env['product.template']._get_additionnal_combination_info(
                self.storable_product, quantity=3, date=datetime(2000, 1, 1), website=self.website
            )
        self.assertFalse(combination_info.get("show_click_and_collect_availability"))
        self.assertFalse(combination_info.get("in_store_stock"))

from odoo import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderLine(SaleCommon):

    def test_get_description_following_lines(self):
        product_2 = self.env["product.product"].create({
            "name": "Test product 2",
            "list_price": 20,
            "description_sale": "First line\nSecond line\nThird line",
        })
        sale_order = self.env['sale.order'].create(
            {
                'partner_id': self.partner.id,
                'company_id': self.company.id,
                'order_line': [
                    Command.create({'product_id': self.product.id}),
                    Command.create({'product_id': self.product.id}),
                    Command.create({'product_id': product_2.id}),
                    Command.create({'product_id': product_2.id}),
                    Command.create({'product_id': product_2.id}),
                ],
            }
        )

        added_desc = "Some important description that should be at the top"
        sale_order.order_line[1].name += "\n" + added_desc
        sale_order.order_line[3].name += "\n" + added_desc
        sale_order.order_line[4].name += "\n" + added_desc
        added_desc_2 = "Some even more important description"
        added_desc_3 = "The most important description"
        sale_order.order_line[4].name += "\n" + added_desc_2
        sale_order.order_line[4].name += "\n" + added_desc_3

        following_lines = list(sale_order.order_line[0].get_description_following_lines())
        self.assertEqual(len(following_lines), 0)
        following_lines = list(sale_order.order_line[1].get_description_following_lines())
        self.assertEqual(len(following_lines), 1)
        self.assertListEqual(following_lines, [added_desc])
        following_lines = list(sale_order.order_line[2].get_description_following_lines())
        self.assertEqual(len(following_lines), 3)
        self.assertListEqual(following_lines, [
            "First line",
            "Second line",
            "Third line"
        ])
        following_lines = list(sale_order.order_line[3].get_description_following_lines())
        self.assertEqual(len(following_lines), 4)
        self.assertListEqual(following_lines, [
            added_desc,
            "First line",
            "Second line",
            "Third line"
        ])
        following_lines = list(sale_order.order_line[4].get_description_following_lines())
        self.assertEqual(len(following_lines), 6)
        self.assertListEqual(following_lines, [
            added_desc_3,
            added_desc_2,
            added_desc,
            "First line",
            "Second line",
            "Third line"
        ])

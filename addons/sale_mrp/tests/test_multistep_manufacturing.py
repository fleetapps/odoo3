# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMultistepManufacturing(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Required for `uom_id ` to be visible in the view
        cls.env.user.group_ids += cls.env.ref('uom.group_uom')
        # Required for `manufacture_steps` to be visible in the view
        cls.env.user.group_ids += cls.env.ref('stock.group_adv_location')
        # Required for `product_id` to be visible in the view
        cls._enable_variants()

        cls.route_mto.active = True
        cls.MrpProduction = cls.env['mrp.production']
        # Create warehouse
        warehouse_form = Form(cls.env['stock.warehouse'])
        warehouse_form.name = 'Test'
        warehouse_form.code = 'Test'
        cls.warehouse = warehouse_form.save()
        cls.warehouse.mto_pull_id.route_id.rule_ids.procure_method = "make_to_order"

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # Create manufactured product
        product_form = Form(cls.env['product.product'])
        product_form.name = 'Stick'
        product_form.uom_id = cls.uom_unit
        product_form.route_ids.clear()
        product_form.route_ids.add(cls.warehouse.manufacture_pull_id.route_id)
        product_form.route_ids.add(cls.warehouse.mto_pull_id.route_id)
        cls.product_manu = product_form.save()

        # Create raw product for manufactured product
        product_form = Form(cls.env['product.product'])
        product_form.name = 'Raw Stick'
        product_form.uom_id = cls.uom_unit
        cls.product_raw = product_form.save()

        # Create bom for manufactured product
        bom_product_form = Form(cls.env['mrp.bom'])
        bom_product_form.product_tmpl_id = cls.product_manu.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'normal'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.product_raw
            bom_line.product_qty = 2.0
        cls.bom_prod_manu = bom_product_form.save()

        # Create sale order
        sale_form = Form(cls.env['sale.order'])
        sale_form.partner_id = cls.env['res.partner'].create({'name': 'My Test Partner'})
        sale_form.picking_policy = 'direct'
        sale_form.warehouse_id = cls.warehouse
        with sale_form.order_line.new() as line:
            line.name = cls.product_manu.name
            line.product_id = cls.product_manu
            line.product_uom_qty = 1.0
            line.price_unit = 10.0
        cls.sale_order = sale_form.save()

    def test_00_manufacturing_step_one(self):
        """ Testing for Step-1 """
        # Change steps of manufacturing.
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'mrp_one_step'
        # Confirm sale order.
        self.sale_order.action_confirm()
        # Check all procurements for created sale order
        mo_procurement = self.MrpProduction.search([('origin', '=', self.sale_order.name)])
        # Get manufactured procurement
        self.assertEqual(mo_procurement.location_src_id.id, self.warehouse.lot_stock_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.location_dest_id.id, self.warehouse.lot_stock_id.id, "Destination location does not match.")
        self.assertEqual(len(mo_procurement), 1, "No Procurement !")

    def test_01_manufacturing_step_two(self):
        """ Testing for Step-2 """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm'
        self.sale_order.action_confirm()
        # Get manufactured procurement
        mo_procurement = self.MrpProduction.search([('origin', '=', self.sale_order.name)])
        mo = self.env['mrp.production'].search([
            ('origin', '=', self.sale_order.name),
            ('product_id', '=', self.product_manu.id),
        ])
        self.assertEqual(self.sale_order.action_view_mrp_production()['res_id'], mo.id)
        self.assertEqual(mo_procurement.location_src_id.id, self.warehouse.pbm_loc_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.location_dest_id.id, self.warehouse.lot_stock_id.id, "Destination location does not match.")

        self.assertEqual(len(mo_procurement), 1, "No Procurement !")

    def test_cancel_multilevel_manufacturing(self):
        """ Testing for multilevel Manufacturing orders.
            When user creates multi-level manufacturing orders,
            and then cancelles child manufacturing order,
            an activity should be generated on parent MO, to notify user that
            demands from child MO has been cancelled.
        """

        product_form = Form(self.env['product.product'])
        product_form.name = 'Screw'
        self.product_screw = product_form.save()

        # Add routes for manufacturing and make to order to the raw material product
        with Form(self.product_raw) as p1:
            p1.route_ids.clear()
            p1.route_ids.add(self.warehouse_1.manufacture_pull_id.route_id)
            p1.route_ids.add(self.warehouse_1.mto_pull_id.route_id)

        # New BoM for raw material product, it will generate another Production order i.e. child Production order
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_tmpl_id = self.product_raw.product_tmpl_id
        bom_product_form.product_qty = 1.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.product_screw
            bom_line.product_qty = 5.0
        self.bom_prod_manu = bom_product_form.save()

        # create MO from sale order.
        self.sale_order.action_confirm()
        # Find child MO.
        child_manufaturing = self.env['mrp.production'].search([('product_id', '=', self.product_raw.id)])
        self.assertTrue((len(child_manufaturing.ids) == 1), 'Manufacturing order of raw material must be generated.')
        # Cancel child MO.
        child_manufaturing.action_cancel()
        manufaturing_from_so = self.env['mrp.production'].search([('product_id', '=', self.product_manu.id)])
        # Check if activity is generated or not on parent MO.
        exception = self.env['mail.activity'].search([('res_model', '=', 'mrp.production'),
                                                      ('res_id', '=', manufaturing_from_so.id)])
        self.assertEqual(len(exception.ids), 1, 'When user cancelled child manufacturing, exception must be generated on parent manufacturing.')

    def test_manufacturing_step_three(self):
        """ Testing for Step-3 """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'
        self.sale_order.action_confirm()

        mo = self.env['mrp.production'].search([
            ('origin', '=', self.sale_order.name),
            ('product_id', '=', self.product_manu.id),
        ])

        self.assertEqual(self.sale_order.mrp_production_count, 1)
        self.assertEqual(mo.sale_order_count, 1)

        self.assertEqual(self.sale_order.action_view_mrp_production()['res_id'], mo.id)
        self.assertEqual(mo.action_view_sale_orders()['res_id'], self.sale_order.id)

    def test_sales_order_with_mto_manufacturing(self):
        self.route_mto.active = True
        warehouse = self.warehouse_1
        warehouse.manufacture_steps = 'pbm_sam'
        prod1 = self.env['product.product'].create({
            'name': 'elct1',
            'type': 'consu',
            'route_ids': [(6, 0, [
                warehouse.manufacture_pull_id.route_id.id,
                warehouse.mto_pull_id.route_id.id
            ])],
        })
        prod2 = self.env['product.product'].create({
            'name': 'elct2',
            'type': 'consu',
            'route_ids': [(6, 0, [
                warehouse.manufacture_pull_id.route_id.id,
                warehouse.mto_pull_id.route_id.id
            ])],
        })
        partner = self.env['res.partner'].create({'name': 'Steve Buscemi'})
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {'product_id': prod1.id, 'product_uom_qty': 1}),
                           (0, 0, {'product_id': prod2.id, 'product_uom_qty': 1})],
            'client_order_ref': 'Test Reference'
        })
        so.action_confirm()

    def test_mto_cancel_3_steps_mo(self):
        '''
        In 3 step manufacturing, test that when the MO gets cancelled, the
        delivery (to the client) can be made from stock.
        '''
        self.warehouse.manufacture_steps = 'pbm_sam'
        self.sale_order.order_line.product_id.is_storable = True
        self.env['stock.quant']._update_available_quantity(
            self.sale_order.order_line.product_id,
            self.sale_order.warehouse_id.lot_stock_id,
            10
        )
        self.sale_order.action_confirm()
        self.assertEqual(self.sale_order.picking_ids.state, 'waiting')
        self.assertEqual(self.sale_order.picking_ids.move_ids.procure_method, 'make_to_order')
        mo = self.sale_order.mrp_production_ids
        self.assertTrue(mo)
        self.assertEqual(self.sale_order.picking_ids.move_ids.move_orig_ids, mo.move_finished_ids)
        mo.action_cancel()
        self.assertEqual(self.sale_order.picking_ids.state, 'confirmed')
        self.assertFalse(self.sale_order.picking_ids.move_ids.move_orig_ids)
        self.sale_order.picking_ids.action_assign()
        self.assertEqual(self.sale_order.picking_ids.move_ids.quantity, 1.0)

    def test_picking_production_ids_shared_picking(self):
        """Test that picking.production_ids returns all linked MOs when a
        picking has moves from multiple production groups.

        In a 2-step manufacturing warehouse (PBM), confirming a sale order
        with two manufactured products creates two MOs — each with its own
        production group. Their PBM moves get separate pickings because
        _search_picking_for_assignation_domain filters by production_group_id.

        When those pickings are later consolidated (e.g. via batch transfer
        or operational merge), the resulting picking has moves from two
        different production groups. The production_ids field must return
        ALL MOs linked through those groups — not just the first one.

        Previously, production_ids used a ``related`` field traversal
        (move_ids.production_group_id.production_ids) which truncated
        intermediate x2many steps via next(iter(...)) in _compute_related,
        silently dropping all production groups after the first.
        """
        self.warehouse.manufacture_steps = 'pbm'
        manufacture_route = self.warehouse.manufacture_pull_id.route_id
        mto_route = self.warehouse.mto_pull_id.route_id

        # Create two manufactured products with their own unique BOMs
        product_a, product_b = self.env['product.product'].create([{
            'name': 'Product A',
            'uom_id': self.uom_unit.id,
            'is_storable': True,
            'route_ids': [(6, 0, [manufacture_route.id, mto_route.id])],
        }, {
            'name': 'Product B',
            'uom_id': self.uom_unit.id,
            'is_storable': True,
            'route_ids': [(6, 0, [manufacture_route.id, mto_route.id])],
        }])
        raw_a, raw_b = self.env['product.product'].create([
            {'name': 'Raw A', 'uom_id': self.uom_unit.id, 'is_storable': True},
            {'name': 'Raw B', 'uom_id': self.uom_unit.id, 'is_storable': True},
        ])
        self.env['mrp.bom'].create([{
            'product_id': product_a.id,
            'product_tmpl_id': product_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {'product_id': raw_a.id, 'product_qty': 1.0})],
        }, {
            'product_id': product_b.id,
            'product_tmpl_id': product_b.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {'product_id': raw_b.id, 'product_qty': 1.0})],
        }])

        # Confirm a sale order with both manufactured products.
        # This organically creates two MOs (each with its own production
        # group) and two PBM pickings — one per production group.
        partner = self.env['res.partner'].create({'name': 'Test Customer'})
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'warehouse_id': self.warehouse.id,
            'order_line': [
                (0, 0, {
                    'name': product_a.name,
                    'product_id': product_a.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 10.0,
                }),
                (0, 0, {
                    'name': product_b.name,
                    'product_id': product_b.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 10.0,
                }),
            ],
        })
        so.action_confirm()

        # Two MOs should be created, each with its own production group
        mos = self.env['mrp.production'].search([('origin', '=', so.name)])
        self.assertEqual(len(mos), 2, "Two MOs should be created for the SO")

        mo_a = mos.filtered(lambda m: m.product_id == product_a)
        mo_b = mos.filtered(lambda m: m.product_id == product_b)
        self.assertEqual(len(mo_a), 1)
        self.assertEqual(len(mo_b), 1)
        self.assertNotEqual(mo_a.production_group_id, mo_b.production_group_id,
            "Each MO must have its own production group")

        # _run_manufacture confirms MOs one-by-one, and
        # _search_picking_for_assignation_domain filters by
        # production_group_id, so each MO gets its own PBM picking.
        pbm_picking_a = mo_a.picking_ids.filtered(
            lambda p: p.picking_type_id == self.warehouse.pbm_type_id)
        pbm_picking_b = mo_b.picking_ids.filtered(
            lambda p: p.picking_type_id == self.warehouse.pbm_type_id)
        self.assertEqual(len(pbm_picking_a), 1)
        self.assertEqual(len(pbm_picking_b), 1)
        self.assertNotEqual(pbm_picking_a, pbm_picking_b)

        # Consolidate both PBM pickings into one — this simulates a batch
        # transfer or operational merge where moves from different production
        # groups end up on the same picking.
        pbm_picking_b.move_ids.picking_id = pbm_picking_a
        pbm_picking_b.unlink()
        picking = pbm_picking_a

        # The picking now has moves from two different production groups
        self.assertEqual(len(picking.move_ids.production_group_id), 2,
            "Picking should have moves from two different production groups")

        # production_ids must return BOTH MOs
        self.assertEqual(len(picking.production_ids), 2,
            "production_ids must return both MOs, not just the first group's")
        self.assertIn(mo_a, picking.production_ids)
        self.assertIn(mo_b, picking.production_ids)
        self.assertEqual(picking.production_count, 2)

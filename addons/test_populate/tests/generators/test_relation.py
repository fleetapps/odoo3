from unittest.mock import patch

from odoo.tests import TransactionCase

from odoo.addons.populate.generators import RelationOne, RelationMany


class TestRelationOne(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.supplier_field = test_product_model._fields['supplier_id']

    def test_relation_generator_basic(self):
        test_suppliers = self.env['test_populate.supplier'].create([
            {'name': 'Test Supplier A', 'country_code': 'US', 'is_active': True},
            {'name': 'Test Supplier B', 'country_code': 'CA', 'is_active': True},
            {'name': 'Test Supplier C', 'country_code': 'US', 'is_active': False},
        ])

        generator = RelationOne(field=self.supplier_field, env=self.env)

        values = [next(generator) for _ in range(50)]

        valid_supplier_ids = test_suppliers.ids
        for value in values:
            self.assertTrue(value is False or value in valid_supplier_ids)

    def test_relation_generator_with_domain(self):
        test_suppliers = self.env['test_populate.supplier'].create([
            {'name': 'US Active Supplier', 'country_code': 'US', 'is_active': True},
            {'name': 'CA Active Supplier', 'country_code': 'CA', 'is_active': True},
            {'name': 'US Inactive Supplier', 'country_code': 'US', 'is_active': False},
        ])

        generator = RelationOne(
            field=self.supplier_field,
            env=self.env,
            domain=[('country_code', '=', 'US'), ('is_active', '=', True)],
        )

        values = [next(generator) for _ in range(30)]

        active_us_suppliers = test_suppliers.filtered(lambda s: s.country_code == 'US' and s.is_active)
        valid_ids = active_us_suppliers.ids

        for value in values:
            self.assertTrue(value is False or value in valid_ids)

    def test_relation_generator_null_frac(self):
        self.env['test_populate.supplier'].create([
            {'name': 'Test Supplier', 'country_code': 'US', 'is_active': True},
        ])

        generator = RelationOne(field=self.supplier_field, env=self.env, null_frac=0.9)

        values = [next(generator) for _ in range(100)]
        false_count = values.count(False)

        self.assertGreater(false_count, 70)

        generator_low_null = RelationOne(field=self.supplier_field, env=self.env, null_frac=0.1)

        values_low_null = [next(generator_low_null) for _ in range(100)]
        false_count_low = values_low_null.count(False)

        self.assertLess(false_count_low, 30)

    def test_relation_generator_empty_recordset(self):
        generator = RelationOne(
            field=self.supplier_field,
            env=self.env,
            domain=[('country_code', '=', 'XYZ')],
        )

        values = [next(generator) for _ in range(20)]

        self.assertTrue(all(value is False for value in values))

    def test_relation_generator_required_field_assertion(self):
        customer_field = self.env['test_populate.order']._fields['customer_id']
        self.assertTrue(customer_field.required)

        ref_gen = RelationOne(field=customer_field, env=self.env, null_frac=0.5)
        self.assertEqual(ref_gen.null_frac, 0)

        generator = RelationOne(field=customer_field, env=self.env, null_frac=0)
        self.assertIsInstance(generator, RelationOne)

    def test_relation_generator_field_type_validation(self):
        generator = RelationOne(field=self.supplier_field, env=self.env)
        self.assertIsInstance(generator, RelationOne)

        name_field = self.env['test_populate.product']._fields['name']
        with self.assertRaises(TypeError):
            RelationOne(field=name_field, env=self.env)


class TestRelationOneSessionBinding(TransactionCase):
    """Test that RelationOne with `ref` + `session` scopes records to that session."""

    def setUp(self):
        super().setUp()
        self.supplier_field = self.env['test_populate.product']._fields['supplier_id']
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Supplier Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'ref': 'my_suppliers',
                    'count': 3,
                    'fields': {'name': {'generator': 'textual.char', 'length': 10}},
                },
            ],
        })

        self.session_a = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        with patch.object(self.env.cr, 'commit', lambda: None):
            self.session_a.start()

        self.session_b = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        with patch.object(self.env.cr, 'commit', lambda: None):
            self.session_b.start()

    def test_ref_without_session_picks_from_all_sessions(self):
        generator = RelationOne(
            field=self.supplier_field,
            env=self.env,
            ref='my_suppliers',
            null_frac=0,
        )

        all_supplier_ids = self.env['populate.model.data'].search([
            ('ref', '=', 'my_suppliers'),
            ('res_model', '=', 'test_populate.supplier'),
        ]).mapped('res_id')

        self.assertEqual(len(all_supplier_ids), 6)
        self.assertEqual(set(generator.comodel_ids), set(all_supplier_ids))

    def test_ref_with_session_scopes_to_that_session(self):
        session_a_supplier_ids = self.env['populate.model.data'].search([
            ('ref', '=', 'my_suppliers'),
            ('session_id', '=', self.session_a.id),
        ]).mapped('res_id')

        session_b_supplier_ids = self.env['populate.model.data'].search([
            ('ref', '=', 'my_suppliers'),
            ('session_id', '=', self.session_b.id),
        ]).mapped('res_id')

        # Scoped to session A
        gen_a = RelationOne(
            field=self.supplier_field,
            env=self.env,
            session=self.session_a,
            ref='my_suppliers',
            null_frac=0,
        )
        self.assertEqual(set(gen_a.comodel_ids), set(session_a_supplier_ids))
        self.assertTrue(set(gen_a.comodel_ids).isdisjoint(set(session_b_supplier_ids)))

        # Scoped to session B
        gen_b = RelationOne(
            field=self.supplier_field,
            env=self.env,
            session=self.session_b,
            ref='my_suppliers',
            null_frac=0,
        )
        self.assertEqual(set(gen_b.comodel_ids), set(session_b_supplier_ids))
        self.assertTrue(set(gen_b.comodel_ids).isdisjoint(set(session_a_supplier_ids)))


class TestRelationMany(TransactionCase):

    def setUp(self):
        super().setUp()
        supplier_model = self.env['test_populate.supplier']
        self.product_ids_field = supplier_model._fields['product_ids']

    def test_relation_many_generator_basic(self):
        test_products = self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
            {'name': 'Product B', 'price': 20.0},
            {'name': 'Product C', 'price': 30.0},
        ])

        generator = RelationMany(field=self.product_ids_field, env=self.env, count=2)

        values = [next(generator) for _ in range(10)]

        for value in values:
            if value:
                selected_ids = value[0][2]
                self.assertEqual(len(selected_ids), 2)
                for product_id in selected_ids:
                    self.assertIn(product_id, test_products.ids)

    def test_relation_many_generator_with_domain(self):
        self.env['test_populate.product'].create([
            {'name': 'Electronics A', 'category': 'electronics', 'price': 10.0},
            {'name': 'Electronics B', 'category': 'electronics', 'price': 20.0},
            {'name': 'Book A', 'category': 'books', 'price': 15.0},
            {'name': 'Book B', 'category': 'books', 'price': 25.0},
        ])

        generator = RelationMany(
            field=self.product_ids_field,
            env=self.env,
            count=2,
            domain=[('category', '=', 'electronics')],
        )

        values = [next(generator) for _ in range(10)]

        electronics_products = self.env['test_populate.product'].search([('category', '=', 'electronics')])
        books_products = self.env['test_populate.product'].search([('category', '=', 'books')])

        for value in values:
            if value:
                selected_ids = value[0][2]
                self.assertEqual(len(selected_ids), 2)
                for product_id in selected_ids:
                    self.assertIn(product_id, electronics_products.ids)
                    self.assertNotIn(product_id, books_products.ids)

    def test_relation_many_generator_null_frac(self):
        self.env['test_populate.product'].create([
            {'name': 'Product 1', 'price': 10.0},
            {'name': 'Product 2', 'price': 20.0},
            {'name': 'Product 3', 'price': 30.0},
        ])

        generator = RelationMany(field=self.product_ids_field, env=self.env, count=2, null_frac=0.9)

        values = [next(generator) for _ in range(100)]
        false_count = values.count(False)

        self.assertGreater(false_count, 70)

    def test_relation_many_generator_count_exceeds_available(self):
        test_products = self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
            {'name': 'Product B', 'price': 20.0},
        ])

        generator = RelationMany(field=self.product_ids_field, env=self.env, count=5)

        value = next(generator)
        if value:
            selected_ids = value[0][2]
            self.assertEqual(len(selected_ids), 2)
            self.assertEqual(set(selected_ids), set(test_products.ids))

    def test_relation_many_generator_field_type_validation(self):
        generator = RelationMany(field=self.product_ids_field, env=self.env, count=1)
        self.assertIsInstance(generator, RelationMany)

        name_field = self.env['test_populate.supplier']._fields['name']
        with self.assertRaises(TypeError):
            RelationMany(field=name_field, env=self.env, count=1)

    def test_relation_many_generator_unique_raises_error(self):
        with self.assertRaises(ValueError) as cm:
            RelationMany(field=self.product_ids_field, env=self.env, count=2, unique=True)

        self.assertIn("Unique cannot be used with the 'relation.many' generator", str(cm.exception))


class TestRelationManySessionBinding(TransactionCase):

    def test_ref_with_session_scopes_to_that_session(self):
        product_ids_field = self.env['test_populate.supplier']._fields['product_ids']

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Product Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'ref': 'tagged_products',
                    'count': 4,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'price': {'generator': 'scalar.float', 'start': 1.0, 'end': 50.0},
                    },
                },
            ],
        })

        session_a = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        with patch.object(self.env.cr, 'commit', lambda: None):
            session_a.start()

        session_b = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        with patch.object(self.env.cr, 'commit', lambda: None):
            session_b.start()

        session_a_product_ids = set(self.env['populate.model.data'].search([
            ('ref', '=', 'tagged_products'),
            ('session_id', '=', session_a.id),
        ]).mapped('res_id'))

        session_b_product_ids = set(self.env['populate.model.data'].search([
            ('ref', '=', 'tagged_products'),
            ('session_id', '=', session_b.id),
        ]).mapped('res_id'))

        # Scoped to session A
        gen_a = RelationMany(
            field=product_ids_field,
            env=self.env,
            session=session_a,
            ref='tagged_products',
            count=2,
            null_frac=0,
        )
        self.assertEqual(set(gen_a.comodel_ids), session_a_product_ids)

        for _ in range(10):
            value = next(gen_a)
            if value:
                selected_ids = set(value[0][2])
                self.assertTrue(selected_ids.issubset(session_a_product_ids))
                self.assertTrue(selected_ids.isdisjoint(session_b_product_ids))

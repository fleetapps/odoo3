from odoo.tests import TransactionCase


class TestDefinitionResolution(TransactionCase):

    def test_resolve_definition(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Resolve Ref Test',
            'definition_json': [
                {'name': 'test_populate.product', 'count': 1, 'fields': {}},
                {'name': 'test_populate.supplier', 'type': 'write', 'ref': 'ref_a', 'fields': {}},
                {'name': 'test_populate.customer', 'type': 'write', 'ref': 'ref_b', 'fields': {}},
                {'name': 'test_populate.order', 'count': 2, 'fields': {}},
                {'name': 'test_populate.customer', 'count': 3, 'ref': 'ref_b', 'fields': {}},
                {'name': 'test_populate.supplier', 'type': 'create', 'count': 4, 'ref': 'ref_a', 'fields': {}},
            ],
        })

        result = blueprint.get_explicit_definition()

        self.assertEqual(len(result), 6)

        self.assertEqual(result[0]['name'], 'test_populate.product')
        self.assertEqual(result[1]['name'], 'test_populate.order')

        ref_a_create_idx = next(i for i, m in enumerate(result) if m.get('ref') == 'ref_a' and m.get('type') != 'write')
        ref_a_write_idx = next(i for i, m in enumerate(result) if m.get('ref') == 'ref_a' and m.get('type') == 'write')
        ref_b_create_idx = next(i for i, m in enumerate(result) if m.get('ref') == 'ref_b' and m.get('type') != 'write')
        ref_b_write_idx = next(i for i, m in enumerate(result) if m.get('ref') == 'ref_b' and m.get('type') == 'write')

        self.assertLess(ref_a_create_idx, ref_a_write_idx)
        self.assertLess(ref_b_create_idx, ref_b_write_idx)

        create_a = result[ref_a_create_idx]
        self.assertEqual(create_a['count'], 4)
        self.assertEqual(create_a['type'], 'create')

    def test_resolve_definition_unresolved_ref(self):
        orphan_blueprint = self.env['populate.blueprint'].create({
            'name': 'Orphan Test',
            'definition_json': [
                {'name': 'test_populate.supplier', 'type': 'write', 'ref': 'orphan', 'fields': {}},
            ],
        })

        with self.assertRaises(RuntimeError) as cm:
            orphan_blueprint.get_explicit_definition()

        self.assertIn('Unresolvable', str(cm.exception))

    def test_normalize_preserves_ref(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Normalize Ref Test',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'ref': 'my_suppliers',
                    'count': 1,
                    'fields': {
                        'product_ids': {
                            'count': 2,
                            'fields': {'name': {'generator': 'textual.char'}},
                        },
                    },
                },
            ],
        })

        resolved = blueprint.get_explicit_definition()

        self.assertEqual(resolved[0]['ref'], 'my_suppliers')
        self.assertEqual(resolved[1]['ref'], 'my_suppliers')


class TestOne2ManyNormalization(TransactionCase):

    def test_normalize_one2many(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Normalize One2Many Test',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'product_ids': {
                            'count': 3,
                            'fields': {
                                'name': {'generator': 'textual.char'},
                                'price': {'generator': 'scalar.float'},
                            },
                        },
                    },
                },
            ],
        })

        resolved = blueprint.get_explicit_definition()

        self.assertEqual(len(resolved), 2)
        self.assertEqual(resolved[0]['name'], 'test_populate.product')
        self.assertEqual(resolved[0]['count'], 6)
        self.assertEqual(resolved[1]['name'], 'test_populate.supplier')
        self.assertIn('ref', resolved[1])
        self.assertEqual(resolved[0]['ref'], resolved[1]['ref'])


class TestMany2ManyNormalization(TransactionCase):

    def test_normalize_many2many(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Normalize Many2Many Test',
            'definition_json': [
                {
                    'name': 'test_populate.product.tagged',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'tag_ids': {
                            'count': 5,
                            'fields': {
                                'name': {'generator': 'textual.char'},
                                'color': {'generator': 'scalar.integer'},
                            },
                        },
                    },
                },
            ],
        })

        resolved = blueprint.get_explicit_definition()

        self.assertEqual(len(resolved), 2)
        self.assertEqual(resolved[0]['name'], 'test_populate.tag')
        self.assertEqual(resolved[0]['count'], 15)
        self.assertEqual(resolved[1]['name'], 'test_populate.product.tagged')


class TestNestedNormalization(TransactionCase):

    def test_normalize_nested_one2many(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Nested One2Many Test',
            'definition_json': [
                {
                    'name': 'test_populate.warehouse',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'supplier_ids': {
                            'count': 3,
                            'fields': {
                                'name': {'generator': 'textual.char'},
                                'product_ids': {
                                    'count': 4,
                                    'fields': {
                                        'name': {'generator': 'textual.char'},
                                        'price': {'generator': 'scalar.float'},
                                    },
                                },
                            },
                        },
                    },
                },
            ],
        })

        resolved = blueprint.get_explicit_definition()

        self.assertEqual(len(resolved), 3)

        self.assertEqual(resolved[0]['name'], 'test_populate.product')
        self.assertEqual(resolved[0]['count'], 24)

        self.assertEqual(resolved[1]['name'], 'test_populate.supplier')
        self.assertEqual(resolved[1]['count'], 6)

        self.assertEqual(resolved[2]['name'], 'test_populate.warehouse')
        self.assertEqual(resolved[2]['count'], 2)

    def test_normalize_mixed_one2many_many2many(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Mixed Nesting Test',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'product_ids': {
                            'count': 3,
                            'fields': {
                                'name': {'generator': 'textual.char'},
                                'tag_ids': {
                                    'count': 4,
                                    'fields': {
                                        'name': {'generator': 'textual.char'},
                                        'color': {'generator': 'scalar.integer'},
                                    },
                                },
                            },
                        },
                    },
                },
            ],
        })

        resolved = blueprint.get_explicit_definition()

        self.assertEqual(len(resolved), 3)

        self.assertEqual(resolved[0]['name'], 'test_populate.tag')
        self.assertEqual(resolved[0]['count'], 24)

        self.assertEqual(resolved[1]['name'], 'test_populate.product')
        self.assertEqual(resolved[1]['count'], 6)

        self.assertEqual(resolved[2]['name'], 'test_populate.supplier')
        self.assertEqual(resolved[2]['count'], 2)

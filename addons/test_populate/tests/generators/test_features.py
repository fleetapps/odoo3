from odoo.tests import TransactionCase

from odoo.addons.populate.generators import (
    Boolean,
    Char,
    Float,
    Generator,
    Integer,
    get_fields_vals,
    NO_VALUE,
)
from odoo.addons.populate.utils.distributions import Distribution


class TestGeneratorUnique(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.name_field = test_product_model._fields['name']
        self.stock_field = test_product_model._fields['stock_quantity']

    def test_generator_unique(self):
        generator = Char(field=self.name_field, env=self.env, length=10, unique=True, null_frac=0)

        values = [next(generator) for _ in range(50)]

        self.assertEqual(len(values), len(set(values)))
        self.assertTrue(all(isinstance(val, str) and len(val) == 10 for val in values))

    def test_generator_unique_with_existing_records(self):
        existing_names = ['ExistName01', 'ExistName02', 'ExistName03']
        self.env['test_populate.product'].create([
            {'name': name, 'price': 10.0} for name in existing_names
        ])

        generator = Char(field=self.name_field, env=self.env, length=11, unique=True, null_frac=0)

        values = [next(generator) for _ in range(20)]

        for value in values:
            self.assertNotIn(value, existing_names)

        self.assertEqual(len(values), len(set(values)))

    def test_unique_generator_exhaustion(self):
        generator = Integer(field=self.stock_field, env=self.env, start=1, end=3, unique=True, null_frac=0)

        values = []
        for _ in range(3):
            values.append(next(generator))

        self.assertEqual(len(set(values)), 3)

        with self.assertRaises(RuntimeError) as cm:
            next(generator)

        self.assertIn("Couldn't find a unique value", str(cm.exception))


class TestGeneratorDepends(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.name_field = test_product_model._fields['name']
        self.price_field = test_product_model._fields['price']
        self.stock_field = test_product_model._fields['stock_quantity']

    def test_generator_depends_basic(self):
        generator = Integer(
            field=self.stock_field,
            env=self.env,
            start=1,
            end=1000,
            depends=['price'],
            null_frac=0,
        )

        value = generator.next({})
        self.assertEqual(value, NO_VALUE)

        value = generator.next({'price': 50.0})
        self.assertIsInstance(value, int)
        self.assertTrue(1 <= value <= 1000)

    def test_generator_depends_multiple_fields(self):
        generator = Char(
            field=self.name_field,
            env=self.env,
            length=10,
            depends=['price', 'category'],
            null_frac=0,
        )

        value = generator.next({})
        self.assertEqual(value, NO_VALUE)

        value = generator.next({'price': 50.0})
        self.assertEqual(value, NO_VALUE)

        value = generator.next({'price': 50.0, 'category': 'electronics'})
        self.assertIsInstance(value, str)
        self.assertEqual(len(value), 10)

    def test_generator_depends_invalid_field(self):
        with self.assertRaises(ValueError) as cm:
            Integer(
                field=self.stock_field,
                env=self.env,
                start=1,
                end=1000,
                depends=['nonexistent_field'],
                null_frac=0,
            )

        self.assertIn("Invalid field dependencies", str(cm.exception))

    def test_generator_depends_with_get_fields_vals(self):
        stock_gen = Integer(
            field=self.stock_field,
            env=self.env,
            start=1,
            end=1000,
            depends=['price'],
            null_frac=0,
        )

        price_gen = Float(
            field=self.price_field,
            env=self.env,
            start=10.0,
            end=100.0,
            null_frac=0,
        )

        generators = {
            'stock_quantity': stock_gen,
            'price': price_gen,
        }

        vals = get_fields_vals(generators)

        self.assertIn('price', vals)
        self.assertIn('stock_quantity', vals)
        self.assertIsInstance(vals['price'], float)
        self.assertIsInstance(vals['stock_quantity'], int)

    def test_generator_depends_circular_dependency_fails(self):
        stock_gen = Integer(
            field=self.stock_field,
            env=self.env,
            start=1,
            end=1000,
            depends=['price'],
            null_frac=0,
        )

        price_gen = Float(
            field=self.price_field,
            env=self.env,
            start=10.0,
            end=100.0,
            depends=['stock_quantity'],
            null_frac=0,
        )

        generators = {
            'stock_quantity': stock_gen,
            'price': price_gen,
        }

        with self.assertRaises(RuntimeError) as cm:
            get_fields_vals(generators)

        self.assertIn("Circular dependency", str(cm.exception))


class TestGeneratorKwargs(TransactionCase):

    def test_get_kwargs(self):
        attrs = {
            'generator': 'textual.char',
            'length': '15',
            'eval': '"static value"',
            'values': "{'a': 3.5, 'b': 1, 'c': 2.1}",
            'domain': "[('active', '=', True)]",
            'unique': 'True',
            'null_frac': '0.3',
            'ref': 'some_reference_model',
            'distribution': 'normal(mean=5, std=8)',
            'unknown_attr': 'should_be_ignored',
        }

        kwargs = Generator.get_kwargs(attrs)
        # partial by default for `get_kwargs`, just make it an instance
        kwargs['distribution'] = kwargs['distribution']()

        expected = {
            'values': {'a': 3.5, 'b': 1, 'c': 2.1},
            'null_frac': 0.3,
            'distribution': Distribution.from_definition('normal(mean=5, std=8)'),
            'unique': True,
        }

        self.assertDictEqual(kwargs, expected)


class TestGeneratorFieldValidation(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.name_field = test_product_model._fields['name']
        self.active_field = test_product_model._fields['active']

    def test_generator_field_type_validation(self):
        boolean_gen = Boolean(field=self.active_field, env=self.env)
        self.assertIsInstance(boolean_gen, Boolean)

        with self.assertRaises(TypeError):
            Boolean(field=self.name_field, env=self.env)


class TestGeneratorInstantiation(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.name_field = test_product_model._fields['name']

    def test_generator_instantiation(self):
        GeneratorChar = Generator.get('textual.char')
        generator = GeneratorChar(field=self.name_field, env=self.env, length=8)

        self.assertIsInstance(generator, Char)
        self.assertEqual(generator.length, 8)


class TestGetFieldsVals(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.name_field = test_product_model._fields['name']
        self.price_field = test_product_model._fields['price']

    def test_get_fields_vals(self):
        name_gen = Char(field=self.name_field, env=self.env, length=10, null_frac=0)
        price_gen = Float(field=self.price_field, env=self.env, start=1.0, end=100.0, null_frac=0)

        generators = {
            'name': name_gen,
            'price': price_gen,
        }

        vals = get_fields_vals(generators)

        self.assertIn('name', vals)
        self.assertIn('price', vals)

        self.assertIsInstance(vals['name'], str)
        self.assertIsInstance(vals['price'], float)

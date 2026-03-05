from odoo.tests import TransactionCase

from odoo.addons.populate.generators import Boolean, Integer, Float


class TestBooleanGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.active_field = test_product_model._fields['active']
        self.is_sellable_field = test_product_model._fields['is_sellable']

    def test_boolean_generator(self):
        for boolean_field, is_required in [
            (self.active_field, False),
            (self.is_sellable_field, True),
        ]:
            self.assertTrue(boolean_field.required == is_required)
            generator = Boolean(field=boolean_field, env=self.env)

            values = [next(generator) for _ in range(100)]

            valid_values = {True, False}
            if not is_required:
                valid_values |= {None}
            self.assertTrue(all(val in valid_values for val in values))

            unique_values = set(values)
            self.assertGreater(len(unique_values), 1)

    def test_boolean_generator_unique_raises_error(self):
        with self.assertRaises(ValueError) as cm:
            Boolean(field=self.active_field, env=self.env, unique=True)

        self.assertIn("Unique cannot be used with the boolean generator", str(cm.exception))


class TestIntegerGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.stock_field = test_product_model._fields['stock_quantity']

    def test_integer_generator(self):
        generator = Integer(field=self.stock_field, env=self.env, start=1, end=1000, null_frac=0)

        values = [next(generator) for _ in range(50)]

        self.assertTrue(all(isinstance(val, int) for val in values))
        self.assertTrue(all(1 <= val <= 1000 for val in values))


class TestFloatGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.price_field = test_product_model._fields['price']

    def test_float_generator(self):
        generator = Float(field=self.price_field, env=self.env, start=10.0, end=100.0, null_frac=0)

        values = [next(generator) for _ in range(100)]

        self.assertTrue(all(isinstance(val, float) for val in values))
        self.assertTrue(all(10.0 <= val <= 100.0 for val in values))

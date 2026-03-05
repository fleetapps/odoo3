from odoo.tests import TransactionCase

from odoo.addons.populate.generators import Eval


class TestEvalGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.name_field = test_product_model._fields['name']
        self.price_field = test_product_model._fields['price']

    def test_eval_generator(self):
        generator = Eval(field=self.name_field, env=self.env, expr='"Test Product"')

        values = [next(generator) for _ in range(10)]

        self.assertTrue(all(val == "Test Product" for val in values))

    def test_eval_generator_numeric(self):
        generator = Eval(field=self.price_field, env=self.env, expr='99.99')

        value = next(generator)
        self.assertEqual(value, 99.99)

    def test_eval_generator_simple_expression(self):
        generator = Eval(field=self.price_field, env=self.env, expr='42 + 69 if True else 420')

        value = next(generator)
        self.assertEqual(value, 111)

    def test_eval_generator_dynamic_with_depends(self):
        generator = Eval(
            field=self.price_field,
            env=self.env,
            expr='price * 2',
            valid_fields=['price'],
        )

        value = generator.send({'price': 50.0})
        self.assertEqual(value, 100.0)

    def test_eval_generator_dynamic_with_multiple_names(self):
        generator = Eval(
            field=self.price_field,
            env=self.env,
            expr='price * stock',
            valid_fields=['price', 'stock'],
        )

        value = generator.send({'price': 10.0, 'stock': 5})
        self.assertEqual(value, 50.0)

    def test_eval_generator_dynamic_correct_name_mapping(self):
        generator = Eval(
            field=self.name_field,
            env=self.env,
            expr="first.lower() + ' ' + second.upper()",
            valid_fields=['first', 'second'],
        )

        name = 'A Product'
        category = 'A Category'
        value = generator.send({'first': name, 'second': category})
        self.assertEqual(value, name.lower() + ' ' + category.upper())

    def test_eval_generator_dynamic_no_accept_lambda(self):
        with self.assertRaises(ValueError):
            Eval(field=self.name_field, env=self.env, expr='lambda x: 42')

    def test_static_generator_unique_raises_error(self):
        with self.assertRaises(ValueError) as cm:
            Eval(field=self.name_field, env=self.env, expr='"Static Value"', unique=True)

        self.assertIn("Eval returns the same value", str(cm.exception))

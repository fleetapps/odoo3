from psycopg2 import IntegrityError

from odoo.tests import TransactionCase


class TestBlueprintDefinition(TransactionCase):

    def test_xml_definition_priority(self):
        json_def = [{'name': 'test_populate.product', 'count': 5, 'fields': {}}]
        xml_def = '<blueprint><model name="test_populate.customer" count="3"></model></blueprint>'

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Priority Test',
            'definition_json': json_def,
            'definition_xml': xml_def,
        })

        parsed_xml_def = [
            {
                'name': 'test_populate.customer',
                'count': 3,
                'fields': {},
            },
        ]
        self.assertEqual(blueprint.definition, parsed_xml_def)

    def test_definition_compute_json_only(self):
        json_def = [
            {
                'name': 'test_populate.product',
                'count': 10,
                'fields': {
                    'name': {'generator': 'textual.char'},
                    'price': {'generator': 'scalar.float'},
                },
            },
        ]

        blueprint = self.env['populate.blueprint'].create({
            'name': 'JSON Only Test',
            'definition_json': json_def,
        })

        self.assertEqual(blueprint.definition, json_def)

    def test_blueprint_with_no_definition_fails(self):
        with self.assertRaises(IntegrityError):
            self.env['populate.blueprint'].create({
                'name': 'Invalid Blueprint',
            })

    def test_blueprint_name_required(self):
        with self.assertRaises(IntegrityError):
            self.env['populate.blueprint'].create({
                'definition_json': [{'name': 'test_populate.product', 'count': 1, 'fields': {}}],
            })

    def test_blueprint_instantiation_creates_jobs(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Instantiation Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 5,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'price': {'generator': 'scalar.float'},
                    },
                },
                {
                    'name': 'test_populate.customer',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'email': {'generator': 'textual.char'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        assert session

        self.assertEqual(len(session.job_ids), 2)

        product_job = session.job_ids.filtered(lambda j: j.model_name == 'test_populate.product')
        customer_job = session.job_ids.filtered(lambda j: j.model_name == 'test_populate.customer')

        self.assertTrue(product_job)
        self.assertTrue(customer_job)

        self.assertEqual(product_job.record_count, 5)
        self.assertEqual(customer_job.record_count, 3)

        self.assertIn('name', product_job.instructions)
        self.assertIn('price', product_job.instructions)
        self.assertIn('name', customer_job.instructions)
        self.assertIn('email', customer_job.instructions)

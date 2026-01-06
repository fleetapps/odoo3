from unittest.mock import patch

from odoo.tests import TransactionCase


class TestUniqueConstraints(TransactionCase):

    def test_char_generator_unique_integration_with_blueprint(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Unique Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'count': 10,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15, 'unique': 'True', 'null_frac': '0'},
                        'email': {'generator': 'textual.char', 'length': 20, 'unique': 'True', 'null_frac': '0'},
                        'age': {'generator': 'scalar.integer', 'start': '18', 'end': '80'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        with patch.object(self.env.cr, 'commit', lambda: None):
            session.start()

        customer_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.customer'),
        ]).mapped('res_id')

        created_customers = self.env['test_populate.customer'].browse(customer_ids)

        names = created_customers.mapped('name')
        self.assertEqual(len(names), len(set(names)))

        emails = created_customers.mapped('email')
        self.assertEqual(len(emails), len(set(emails)))

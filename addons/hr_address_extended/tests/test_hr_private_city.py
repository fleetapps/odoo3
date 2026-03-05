from odoo.tests import tagged, HttpCase


@tagged('at_install', '-post_install')
class TestHrPrivateCity(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_us = cls.env.ref('base.us')
        cls.country_us.enforce_cities = True        
        cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'private_country_id': cls.country_us.id,
        })

    def test_employee_private_city(self):
        self.start_tour("/odoo", 'private_city_test', login="admin", timeout=350)

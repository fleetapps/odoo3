from odoo.tests import TransactionCase

from odoo.addons.populate.utils.orm import VirtualField, drop_pending_update


class TestVirtualField(TransactionCase):

    def test_virtual_field_creation(self):
        vf = VirtualField('test_populate.product', 'test_field')
        self.assertEqual(vf.model_name, 'test_populate.product')
        self.assertEqual(vf.name, 'test_field')
        self.assertEqual(vf.type, 'virtual')
        self.assertFalse(vf.required)

    def test_virtual_field_str(self):
        vf = VirtualField('test_populate.product', 'test_field')
        self.assertEqual(str(vf), 'test_populate.product.test_field')

    def test_virtual_field_repr(self):
        vf = VirtualField('test_populate.product', 'test_field')
        self.assertEqual(repr(vf), "VirtualField('test_populate.product', 'test_field')")


class TestDropPendingUpdate(TransactionCase):

    def test_drop_pending_update_with_dirty_fields(self):
        product = self.env['test_populate.product'].create({
            'name': 'Test Product',
            'price': 100.0,
        })

        product.name = 'Modified Product'

        name_field = self.env['test_populate.product']._fields['name']

        self.assertTrue(self.env.transaction.field_dirty[name_field])

        drop_pending_update(self.env, ['name'])

        self.assertFalse(self.env.transaction.field_dirty[name_field])

    def test_drop_pending_update_only_specified_fields(self):
        product = self.env['test_populate.product'].create({
            'name': 'Test Product',
            'price': 100.0,
        })

        product.name = 'Modified Product'
        product.price = 420

        name_field = self.env['test_populate.product']._fields['name']
        price_field = self.env['test_populate.product']._fields['price']

        self.assertTrue(self.env.transaction.field_dirty[name_field])
        self.assertTrue(self.env.transaction.field_dirty[price_field])

        drop_pending_update(self.env, ['name'])

        self.assertFalse(self.env.transaction.field_dirty[name_field])
        self.assertTrue(self.env.transaction.field_dirty[price_field])

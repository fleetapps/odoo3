from odoo import Command, fields
from odoo.exceptions import LockError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAccountMoveEventProcess(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})],
        })

    def test_schedule_events(self):
        event_code = 'test_event'
        data = {'key': 'value'}
        self.env['account.move.event.process'].schedule_events([{
            'move': self.invoice,
            'event_code': event_code,
            'data': data,
        }])
        event = self.env['account.move.event.process'].search([
            ('move_id', '=', self.invoice.id),
            ('event_code', '=', event_code),
        ])
        self.assertTrue(event)
        self.assertEqual(event.data, data)
        self.assertEqual(event.state, 'new')

    def test_get_move_active_event_data(self):
        event_code = 'test_event'
        self.env['account.move.event.process'].schedule_events([
            {'move': self.invoice, 'event_code': event_code, 'data': {'v': 1}, 'scheduled_at': fields.Datetime.now()},
        ])

        data = self.env['account.move.event.process'].get_move_active_event_data(
            self.invoice,
            'test_event',
        )
        self.assertEqual(data['v'], 1)

    def test_reschedule_events(self):
        event_code = 'reschedule_event'
        self.env['account.move.event.process'].schedule_events([
            {'move': self.invoice, 'event_code': event_code, 'data': {'v': 1}},
        ])
        self.env['account.move.event.process'].search([
            ('move_id', '=', self.invoice.id),
            ('event_code', '=', event_code),
        ]).state = 'done'

        self.env['account.move.event.process'].flush_model(['state'])

        self.env['account.move.event.process'].reschedule_events([
            {'move': self.invoice, 'event_code': event_code},
        ])
        events = self.env['account.move.event.process'].search([
            ('move_id', '=', self.invoice.id),
            ('event_code', '=', event_code),
        ])
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].data['v'], events[1].data['v'])

    def test_get_batch_to_process(self):
        event_code = 'concurrent_event'
        self.env['account.move.event.process'].schedule_events([{
            'move': self.invoice,
            'event_code': event_code,
        }])
        events = self.env['account.move.event.process'].get_batch_to_process(event_code)
        self.assertEqual(len(events), 1)

        with self.assertRaises(LockError), self.env.registry.cursor() as cr:
            self.env(cr=cr)['account.move.event.process'].browse(events.ids).lock_for_update()

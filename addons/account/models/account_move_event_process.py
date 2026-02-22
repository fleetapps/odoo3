from datetime import timedelta

from odoo import api, fields, models


class AccountMoveEventProcess(models.Model):
    _name = 'account.move.event.process'
    _description = 'Account Move Event Process'

    event_code = fields.Char(required=True, index=True)
    state = fields.Selection([
        ('new', 'New'),
        ('done', 'Done'),
    ], default='new', required=True, copy=False)
    scheduled_at = fields.Datetime(default=fields.Datetime.now, required=True)
    data = fields.Json()
    move_id = fields.Many2one('account.move', required=True)

    _state_event_code_scheduled_at_idx = models.Index('(state, event_code, scheduled_at)')
    _unique_model_id_res_id_event_code = models.UniqueIndex(
        "(move_id, event_code) WHERE state = 'new'",
        "Can not schedule more than one event per move at a time.",
    )

    @api.model
    def get_move_active_event_data(self, move, event_code):
        """Gets JSON data of the most recently scheduled, unprocessed event for a single move."""
        move.ensure_one()
        domain = [
            ('state', '=', 'new'),
            ('event_code', '=', event_code),
            ('move_id', '=', move.id),
        ]
        if event := self.search(domain, order='scheduled_at desc'):
            return event.data
        return None

    def get_batch_to_process(self, event_code, batch_size=100):
        """Gets a batch of pending events and locks them for processing."""
        events = self.search(
            [
                ('event_code', '=', event_code),
                ('state', '=', 'new'),
            ],
            order='scheduled_at asc',
            limit=batch_size,
        )
        events.lock_for_update()
        return events

    @api.model
    def schedule_events(self, values):
        """
        Schedules new events.
        :param values: A list of dictionaries. Expected keys:
        {
           move: The `account.move` object you want to do the event on.
           event_code: The code of the event.
           data: JSON payload for the event. Defaults to {}.
           scheduled_at: Timestamp for the event. Defaults to now.
        }
        """
        vals_list = [
            {
                'move_id': val['move'].id,
                'event_code': val['event_code'],
                'data': val.get('data', {}),
                'scheduled_at': val.get('scheduled_at', fields.Datetime.now()),
            } for val in values
        ]
        self.create(vals_list)

    def reschedule_events(self, values):
        """
        Duplicates existing events that match the provided records and event code.
        All dictionaries in the 'values' list must share the same 'event_code'
        and target the same underlying model.
        :param values: A list of dictionaries. Expected keys:
        {
            move: The `account.move` object you want to reschedule its event.
            event_code: The code of the event to reschedule.
        }
        """
        event_code = values[0]['event_code']
        moves = self.env['account.move']

        for val in values:
            moves |= val['move']

        self.search(
            [
                ('event_code', '=', event_code),
                ('move_id', 'in', moves.ids),
                ('state', '=', 'new'),
            ],
        ).copy()

    @api.model
    def _cron_clean_events(self):
        self.search(
            [
                ('state', '=', 'done'),
                ('scheduled_at', '<', fields.Datetime.now() - timedelta(days=1)),
            ],
        ).unlink()

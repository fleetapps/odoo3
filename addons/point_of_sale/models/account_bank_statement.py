# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_session_id = fields.Many2one('pos.session', string="Session", copy=False, index='btree_not_null')

    @api.model_create_multi
    def create(self, vals_list):
        journal_ids = {vals['journal_id'] for vals in vals_list if vals.get('journal_id')}

        if journal_ids and (sessions := self.env['pos.session'].sudo().search([
                ('cash_journal_id', 'in', list(journal_ids)),
                ('state', '=', 'opening_control'),
            ])):
            session_by_journal = {
                session.cash_journal_id.id: session
                for session in sessions
            }

            amounts_by_journal = {}
            for vals in vals_list:
                journal_id = vals.get('journal_id')
                if session_by_journal.get(journal_id):
                    amounts_by_journal[journal_id] = amounts_by_journal.get(journal_id, 0.0) + vals.get('amount', 0.0)

            for journal_id, total_amount in amounts_by_journal.items():
                session = session_by_journal.get(journal_id)
                session.cash_register_balance_start += total_amount
                session.config_id._notify(('SESSION_UPDATED', {'session_id': session.id}))

        return super().create(vals_list)

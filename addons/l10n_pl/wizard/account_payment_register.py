from datetime import datetime
import json
import requests

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin


class PlNipError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class L10nPlAccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # Technical field containing datas for each batch, used to create payments
    l10n_pl_bank_verification_data = fields.Json(compute='_compute_l10n_pl_bank_verification_data')
    # partners whose (vat/bank account) link is not referenced in gov api
    l10n_pl_bank_verification_invalid_partner_ids = fields.Many2many(comodel_name='res.partner', compute='_compute_l10n_pl_bank_verification_invalid_partner_ids')
    # partners whose vat cannot be found in gov api
    l10n_pl_not_found_partner_ids = fields.Many2many(comodel_name='res.partner', compute='_compute_l10n_pl_bank_verification_invalid_partner_ids')
    # partners who do not have a VAT number or bank account (-> internal, no api call)
    l10n_pl_incomplete_data_partner_ids = fields.Many2many(comodel_name='res.partner', compute='_compute_l10n_pl_bank_verification_data')

    @api.depends('line_ids', 'partner_bank_id')
    def _compute_l10n_pl_bank_verification_data(self):

        def get_not_required_batch_obj(batch):
            return {
                'lines': batch['lines'],
                'status': 'not_required',
            }

        for wizard in self:
            # Early skip if company not PL
            if wizard.company_id.country_code != 'PL':
                wizard.l10n_pl_bank_verification_data = [
                    get_not_required_batch_obj(batch) for batch in wizard.batches
                ]
                wizard.l10n_pl_incomplete_data_partner_ids = self.env['res.partner']
                continue

            to_check = []
            not_required = []
            for batch in wizard.batches:
                if self._batch_need_check(batch):
                    to_check.append(batch)
                else:
                    not_required.append(get_not_required_batch_obj(batch))

            datas, incomplete_partner_ids = self._check_partners(to_check)
            wizard.l10n_pl_bank_verification_data = datas + not_required
            wizard.l10n_pl_incomplete_data_partner_ids = self.env['res.partner'].browse(incomplete_partner_ids)

    @api.depends('l10n_pl_bank_verification_data')
    def _compute_l10n_pl_bank_verification_invalid_partner_ids(self):
        for wizard in self:
            invalid_partner_ids = []
            not_foud_partner_ids = []
            for data in wizard.l10n_pl_bank_verification_data:
                if data['status'] == 'invalid':
                    invalid_partner_ids.append(data['partner'])
                elif data['status'] == 'invalid_nip':
                    not_foud_partner_ids.append(data['partner'])
            wizard.l10n_pl_bank_verification_invalid_partner_ids = self.env['res.partner'].browse(invalid_partner_ids)
            wizard.l10n_pl_not_found_partner_ids = self.env['res.partner'].browse(not_foud_partner_ids)

    @api.model
    def _batch_need_check(self, batch):
        """
        Does batch need a government API call to check if the partner vat is linked to its account number
        """
        # Check partner is PL
        partner = self.env['res.partner'].browse(batch['payment_values']['partner_id'])
        if partner.country_code != 'PL':
            return False

        # Check batch is not outbound
        if batch['payment_values']['payment_type'] != 'outbound':
            return False

        moves = self.env['account.move.line'].browse(batch['lines']).move_id
        pln = self.env.ref('base.PLN', raise_if_not_found=False)

        # Check currency = PLN and move brut amount is 15.000 PLN or more
        return any(move.currency_id == pln and pln.compare_amounts(move.amount_total, 15000.0) >= 0 for move in moves)

    @api.model
    def _check_partners(self, batches, date=None):
        """
        Sort batches to check, call API and build results
        :param batches: Batches to sort and check
        :param date: date to check batches
        :return: Datas for each batch
        """
        date = date or datetime.now().date()
        results = []
        incomplete_partner_ids = []
        if not batches:
            return results, incomplete_partner_ids

        batches_to_check = []
        nips_to_check = set()

        for batch in batches:
            partner = self.env['res.partner'].browse(batch['payment_values']['partner_id'])
            # Check partner has VAT and bank account (in odoo)
            valid_partner_values = self._check_batch_partner_values(partner, batch)
            if not valid_partner_values:
                incomplete_partner_ids.append(partner.id)
                results.append({'lines': batch['lines'], 'status': 'incomplete'})
                continue
            # Check if partner bank accounts have already been checked for date
            if bank_account_status := self._bank_account_already_checked(partner, batch, date):
                results.append({
                    'lines': batch['lines'],
                    **bank_account_status,
                })
            else:
                batches_to_check.append(batch)
                nips_to_check.add(partner.vat)

        if len(nips_to_check) == 0:
            return results, incomplete_partner_ids

        # create endpoints to call, API support 30 vat numbers per request
        endpoints = []
        if len(nips_to_check) == 1:
            endpoints.append(f'/search/nip/{next(iter(nips_to_check))}')
        else:
            nips = list(nips_to_check)
            for i in range(int(len(nips_to_check) / 30) + 1):
                endpoints.append(f'/search/nips/{",".join(nips[i * 30:i * 30 + 30])}')

        # Call api for each endpoint
        for endpoint in endpoints:
            try:
                response = self._make_request(endpoint, params={'date': date})
                response_content = self._handle_response(response)
            except PlNipError:
                # Handle error case where vat is not found
                results = results + [{
                    'lines': batch['lines'],
                    'partner': batch['payment_values']['partner_id'],
                    'status': 'invalid_nip',
                } for batch in batches_to_check]
                continue
            datas = json.loads(response_content)['result']
            results = results + self._get_batches_status_from(datas, batches_to_check)
        return results, incomplete_partner_ids

    @api.model
    def _check_batch_partner_values(self, partner, batch):
        """
        Check if the partner of the batch has a VAT number and bank accounts assigned
        :param partner: The partner concerned by the batch
        :param batch: The batch to check
        :return: True if partner is valid, False otherwise
        """
        if partner._is_vat_void(partner.vat):
            return False

        if partner_bank_id := batch['payment_values']['partner_bank_id']:
            partner_banks = self.env['res.partner.bank'].browse(partner_bank_id)
        else:
            partner_banks = partner.bank_ids

        return bool(partner_banks)

    def _bank_account_already_checked(self, partner, batch, date):
        """
        Check if bank accounts of the partner were already checked at date
        :param partner: The partner concerned by the batch
        :param batch: The batch to check
        :param date: Date
        :return: False if bank accounts weren't checked, a dict with {status/request_datetime/request_id} otherwise
        """
        if partner_bank_id := batch['payment_values']['partner_bank_id']:
            partner_banks = self.env['res.partner.bank'].browse(partner_bank_id)
        else:
            partner_banks = partner.bank_ids
        if all(partner_bank._l10n_pl_status_at_date in ('valid', 'invalid') for partner_bank in partner_banks):
            partner_bank = partner_banks[0]
            return {
                'status': partner_bank._l10n_pl_status_at_date,
                'request_datetime': partner_bank.l10n_pl_bank_verification_timestamp,
                'request_id': partner_bank.l10n_pl_bank_verification_request_id,
            }
        return False

    def _make_request(self, endpoint, params=None):
        """
        Send request to the government API
        :param endpoint: The endpoint to call on the API
        :param params: Params to include in request
        :return: response
        """
        params = params or {}
        url = urljoin('https://wl-api.mf.gov.pl/api', endpoint)
        response = requests.request(
            'GET',
            url,
            headers={'Content-Type': 'application/json'},
            params=params,
            timeout=5,
        )
        return response

    def _handle_response(self, response):
        """
        Handle response given by the API
        :param response: The response received by the API
        :return: Response content or raise an error
        """
        if response.status_code == 200:
            return response.content.decode()
        elif response.status_code == 400:
            content = json.loads(response.content.decode())
            if content['code'] in ['WL-113', 'WL-115']:  # 113: incorrect format, 115: nip not found
                raise PlNipError(self.env._("The partner has an invalid nip"))
            else:
                raise ValidationError(self.env._("An unknown error occurred while calling the government API. Please contact support with the following information:\n"
                                        "Status code: %(status_code)s\n"
                                        "Error message: %(msg)s", status_code=response.status_code, msg=response.content.decode()))
        elif 500 <= response.status_code < 600:
            raise ValidationError(self.env._("An error occurred during call to government API. Please try again later"))
        else:
            raise ValidationError(self.env._("An unknown error occurred while calling the government API. Please contact support with the following information:\n"
                                    "Status code: %(status_code)s\n"
                                    "Error message: %(msg)s", status_code=response.status_code, msg=response.content.decode()))

    def _get_batches_status_from(self, datas, batches):
        """
        Convert datas into objects like following and also retrieves request ID and timestamp
        [{
            'lines': [252],
            'partner': 45,
            'nip': '1111111111',
            'account_numbers': ["90249000050247256316596736", "90249000050247256316596737"],
            'status': 'valid'|'invalid'|'not_required',
            'request_datetime': '20260216 090000',
            'request_id': 'd2n10-84df1a1',
        }]
        :param datas: Datas received by the API
        :param batches: Batches concerned by the API call
        :return: a dict like described above
        """
        request_id = datas['requestId']
        timestamp = datetime.strptime(datas['requestDateTime'], "%d-%m-%Y %H:%M:%S")
        results = []

        for entry in datas.get('entries', [datas]):
            # Case where multiple vat were checked, and one or multiple were invalid
            identifier = entry.get('identifier')
            if entry.get('error'):
                partner = self.env['res.partner'].search([('vat', '=', identifier)], limit=1)
                partner_batches = list(filter(lambda batch: batch['payment_values']['partner_id'] == partner.id, batches))
                results = results + [{
                    'lines': batch['lines'],
                    'status': 'invalid_nip',
                    'partner': partner.id,
                } for batch in partner_batches]
                continue

            subject = entry.get('subjects', [entry.get('subject')])[0]
            account_numbers_from_gov = subject['accountNumbers']
            identifier = identifier or subject['nip']
            partner = self.env['res.partner'].search([('vat', '=', identifier)], limit=1)
            partner_batches = list(filter(lambda batch: batch['payment_values']['partner_id'] == partner.id, batches))
            for batch in partner_batches:
                if partner_bank_id := batch['payment_values']['partner_bank_id']:
                    partner_banks = self.env['res.partner.bank'].browse(partner_bank_id)
                else:
                    partner_banks = partner.bank_ids
                status = all(
                    bank_account.account_number.removeprefix('PL').replace(' ', '') in account_numbers_from_gov
                    for bank_account in partner_banks
                )
                partner_banks.write({
                    'l10n_pl_bank_verification_status': 'valid' if status else 'invalid',
                    'l10n_pl_bank_verification_request_id': request_id,
                    'l10n_pl_bank_verification_timestamp': timestamp,
                })
                results.append({
                    'lines': batch['lines'],
                    'partner': partner.id,
                    'request_id': request_id,
                    'request_datetime': timestamp,
                    'nip': identifier,
                    'account_numbers': account_numbers_from_gov,
                    'status': 'valid' if status else 'invalid',
                })

        return results

    def _create_payment_vals_from_wizard(self, batch_result):
        # EXTENDS account
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        return self._update_payment_vals(payment_vals, batch_result)

    def _create_payment_vals_from_batch(self, batch_result):
        # EXTENDS account
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        return self._update_payment_vals(payment_vals, batch_result)

    @api.model
    def _update_payment_vals(self, payment_vals, batch_result):
        payment_data = next(data for data in self.l10n_pl_bank_verification_data if set(batch_result['lines'].ids) & set(data['lines']))
        payment_vals['l10n_pl_bank_verification_status'] = payment_data['status']
        if payment_data['status'] in ('valid', 'invalid'):
            payment_vals.update({
                'l10n_pl_bank_verification_timestamp': payment_data['request_datetime'],
                'l10n_pl_bank_verification_request_id': payment_data['request_id'],
            })
        return payment_vals

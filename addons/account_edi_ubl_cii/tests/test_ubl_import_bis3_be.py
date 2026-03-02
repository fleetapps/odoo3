from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3BE(TestUblBis3Common, TestUblCiiBECommon):

    @freeze_time('2020-01-01')
    def test_import_partner(self):
        self.partner_be.unlink()
        self.assertFalse(self.env['res.partner'].search([('vat', '=', 'BE0477472701')]))

        # Test the partner has been created.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_partner',
            journal=self.company_data['default_journal_sale'],
        )
        partner = invoice.partner_id
        self.assertRecordValues(partner, [{
            'name': "My Belgian Partner",
            'street': "Rue des Trucs 9",
            'city': "Bidule",
            'zip': "6713",
            'vat': 'BE0477472701',
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
        }])

        # Test the partner has been retrieved.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_partner',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice.partner_id, [{'id': partner.id}])

    @freeze_time('2020-01-01')
    def test_import_discount_per_line_price_on_big_quantity(self):
        tax_21 = self.percent_tax(21.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_discount_per_line_price_on_big_quantity',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 150.0,
                    'price_unit': 0.5307333333333333,
                    'discount': 11.995980404471794,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 200.0,
                    'price_unit': 0.6369,
                    'discount': 12.003454231433523,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 182.15,
                    'amount_tax': 38.25,
                    'amount_total': 220.40,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_import_lot_of_decimals_in_quantities(self):
        tax_21 = self.percent_tax(21.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_lot_of_decimals_in_quantities',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 0.93,
                    'price_unit': 101.34642857142858,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 0.28,
                    'price_unit': 101.36470588235294,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 0.5,
                    'price_unit': 126.7,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 6.45,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 14.44,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 25.79,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 233.34,
                    'amount_tax': 49.0,
                    'amount_total': 282.34,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_import_not_matched_tax(self):
        """ The tax has not been retrieved. Do not store any 'extra_tax_data'. """
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_discount_per_line_price_on_big_quantity',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 150.0,
                    'price_unit': 0.5307333333333333,
                    'discount': 11.995980404471794,
                    'tax_ids': [],
                },
                {
                    'quantity': 200.0,
                    'price_unit': 0.6369,
                    'discount': 12.003454231433523,
                    'tax_ids': [],
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 182.15,
                    'amount_tax': 0.0,
                    'amount_total': 182.15,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_import_mixed_allowance_charges(self):
        tax_25 = self.percent_tax(25.0)
        tax_0 = self.percent_tax(0.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_mixed_allowance_charges',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                # Invoice line 1
                {
                    'quantity': 10.0,
                    'price_unit': 450.0,
                    'discount': 11.133333333333338,
                    'tax_ids': tax_25.ids,
                },
                # Invoice line 1, charge.
                {
                    'quantity': 1.0,
                    'price_unit': 1.0,
                    'discount': 0.0,
                    'tax_ids': tax_25.ids,
                },
                # Invoice line 2
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'discount': 0.0,
                    'tax_ids': tax_0.ids,
                },
                # Invoice line 3
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'discount': 10.100000000000007,
                    'tax_ids': tax_25.ids,
                },
                # Invoice line 3, charge
                {
                    'quantity': 1.0,
                    'price_unit': 1.0,
                    'discount': 0.0,
                    'tax_ids': tax_25.ids,
                },
                # Invoice global charge
                {
                    'quantity': 0.2,
                    'price_unit': 1000.0,
                    'discount': 0.0,
                    'tax_ids': tax_25.ids,
                },
                # Invoice global allowance
                {
                    'quantity': 1.0,
                    'price_unit': -200.0,
                    'discount': 0.0,
                    'tax_ids': tax_25.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 5900.0,
                    'amount_tax': 1225.0,
                    'amount_total': 7125.0,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_import_predictive_invoice_matched_tax_and_account(self):
        tax_21_1 = self.percent_tax(21.0, sequence=1)
        tax_21_2 = self.percent_tax(21.0, sequence=2)
        default_account = self.company_data['default_account_revenue']
        new_account = default_account.copy()

        # Retrieve the tax having the lower sequence.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_discount_per_line_price_on_big_quantity',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'tax_ids': tax_21_1.ids,
                'account_id': default_account.id,
            }] * 2,
        )

        # Same with an existing invoice using the other.
        self._create_invoice(
            partner_id=invoice.partner_id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    name='Cheville légères HLD 2',
                    price_unit=1234.56,
                    tax_ids=tax_21_2,
                    account_id=new_account,
                )
            ],
            post=True,
        )

        # Retrieve the tax having the lower sequence.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_discount_per_line_price_on_big_quantity',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'tax_ids': tax_21_2.ids,
                'account_id': new_account.id,
            }] * 2,
        )

    @freeze_time('2020-01-01')
    def test_import_predictive_invoice_matched_multiple_taxes_same_rate(self):
        """ In the xml, we retrieve a total for a 21.0% tax rate. However, the prediction
        finds a different 21% tax for each line.
        """
        tax_21_1 = self.percent_tax(21.0)
        tax_21_2 = self.percent_tax(21.0)

        self._create_invoice(
            partner_id=self.partner_be.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    name='Cheville légères HLD 2',
                    price_unit=1234.56,
                    tax_ids=tax_21_1,
                ),
                self._prepare_invoice_line(
                    name='Vis pour cheville HLD 3',
                    price_unit=1234.56,
                    tax_ids=tax_21_2,
                ),
            ],
            post=True,
        )

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_discount_per_line_price_on_big_quantity',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 150.0,
                    'price_unit': 0.5307333333333333,
                    'discount': 11.995980404471794,
                    'tax_ids': tax_21_1.ids,
                },
                {
                    'quantity': 200.0,
                    'price_unit': 0.6369,
                    'discount': 12.003454231433523,
                    'tax_ids': tax_21_2.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 182.15,
                    'amount_tax': 38.25,
                    'amount_total': 220.40,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_import_cash_rounding_add_invoice_line(self):
        tax_21 = self.percent_tax(21.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_cash_rounding_add_invoice_line',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 899.99,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 0.01,
                    'tax_ids': [],
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 900.0,
                    'amount_tax': 189.0,
                    'amount_total': 1089.0,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_import_cash_rounding_biggest_tax(self):
        tax_21 = self.percent_tax(21.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_cash_rounding_biggest_tax',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 899.99,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 899.99,
                    'amount_tax': 189.01,
                    'amount_total': 1089.0,
                },
            ],
        )

    # -------------------------------------------------------------------------
    # PARTIAL IMPORTS
    # -------------------------------------------------------------------------

    def test_partial_import_invoice_line_name_and_description(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_name_and_description')
        self.assertRecordValues(invoice.invoice_line_ids, [{'name': 'description value'}])

    def test_partial_import_invoice_line_name(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_name')
        self.assertRecordValues(invoice.invoice_line_ids, [{'name': 'name value'}])

    def test_partial_import_invoice_line_only_line_extension_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_only_line_extension_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 899.99,
            'quantity': 1.0,
        }])

    def test_partial_import_invoice_line_line_extension_amount_plus_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_plus_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 179.998,
            'quantity': 5.0,
        }])

    def test_partial_import_invoice_line_line_extension_amount_plus_quantity_plus_allowance_plus_charge(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_plus_quantity_plus_allowance_plus_charge')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 200.0,
                'quantity': 5.0,
                'discount': 10.000000000000007,
            },
            {
                'price_unit': 50.0,
                'quantity': 1.0,
                'discount': 0.0,
            },
        ])

    def test_partial_import_invoice_line_price_amount_plus_base_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_price_amount_plus_base_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 90.0,
            'quantity': 5.0,
        }])

    def test_partial_import_invoice_line_price_amount_plus_base_quantity_plus_allowance(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_price_amount_plus_base_quantity_plus_allowance')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 90.0,
            'quantity': 5.0,
        }])

    def test_partial_import_invoice_line_line_extension_amount_weird_0_quantity_and_0_price_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_weird_0_quantity_and_0_price_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1000.0,
            'quantity': 1.0,
            'discount': 0.0,
            'price_subtotal': 1000.0,
        }])

    def test_partial_import_invoice_line_line_extension_amount_weird_0_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_weird_0_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 100.0,
            'quantity': 10.0,
            'discount': 0.0,
            'price_subtotal': 1000.0,
        }])

    def test_partial_import_invoice_line_line_extension_amount_weird_0_price_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_weird_0_price_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 10.0,
            'quantity': 100.0,
            'discount': 0.0,
            'price_subtotal': 1000.0,
        }])

    def test_partial_import_invoice_line_negative_lines_and_total(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_negative_lines_and_total')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 400.0,
                'quantity': 7.000000000000005,
                'discount': 0.0,
                'price_subtotal': 2800.0,
            },
            {
                'price_unit': 500.0,
                'quantity': -3.000000000000003,
                'discount': 0.0,
                'price_subtotal': -1500.0,
            },
        ])

    def test_partial_import_invoice_line_product(self):
        products = self.env['product.product'].create([{
            'name': 'XYZ',
            'default_code': '1234',
        }, {
            'name': 'XYZ',
            'default_code': '5678',
        }, {
            'name': 'XXX',
            'default_code': '1111',
            'barcode': '00001',
        }, {
            'name': 'YYY',
            'default_code': '1111',
            'barcode': '00002',
        }])

        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_product_1')
        self.assertRecordValues(invoice.invoice_line_ids, [{'product_id': products[0].id}])

        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_product_2')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {'product_id': products[0].id},
            {'product_id': products[1].id},
            {'product_id': products[2].id},
            {'product_id': products[3].id},
        ])

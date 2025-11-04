from odoo import models


class AccountEdiXmlUblGr(models.AbstractModel):
    _name = 'account.edi.xml.ubl_gr'
    _inherit = 'account.edi.xml.ubl_bis3'
    _description = "CIUS GR"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_gr_peppol_cius.xml"

    def _format_greek_invoice_number(self, invoice):
        # GR-R-001-2: First segment - VAT without EL prefix
        company_vat = invoice.company_id.vat
        if company_vat.startswith('EL'):
            company_vat = company_vat[2:]
        # GR-R-001-3: Second segment - Issue date DD/MM/YYYY
        issue_date = invoice.invoice_date.strftime('%d/%m/%Y')
        # GR-R-001-4: Third segment - Installation serial(branch number)
        installation_sn = str(invoice.company_id.l10n_gr_edi_branch_number)
        # GR-R-001-5: Fourth segment - Valid Greek document type
        invoice_type = invoice.l10n_gr_edi_inv_type
        # GR-R-001-6: Fifth segment - Series
        series = invoice.name.split('/')[0]
        # GR-R-001-7: Sixth segment - Serial number
        serial_number = invoice.name.split('/')[-1]
        return f"{company_vat}|{issue_date}|{installation_sn}|{invoice_type}|{series}|{serial_number}"

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']
        document_node.update({
            # BT-1: Invoice number with format: "VAT|Issue date|Installation sn.|Invoice Type|Series|eINV Issue sn."
            'cbc:ID': {'_text': self._format_greek_invoice_number(invoice)},
        })
        # BT-10: Buyer reference - Contracting authority name (only for B2G transactions)
        if invoice.partner_id.l10n_gr_edi_contracting_authority_name:
            document_node['cbc:BuyerReference'] = {'_text': invoice.partner_id.l10n_gr_edi_contracting_authority_name}

    # -------------------------------------------------------------------------
    # EXPORT VALUES
    # -------------------------------------------------------------------------

    def _get_invoice_node(self, vals):
        document_node = super()._get_invoice_node(vals)
        invoice = vals['invoice']
        if vals['document_type'] != 'credit_note':
            # BT-11: ProjectReference
            if invoice.l10n_gr_edi_budget_type and invoice.l10n_gr_edi_project_reference:
                document_node['cac:ProjectReference'] = {
                    'cbc:ID': {'_text': f"{invoice.l10n_gr_edi_budget_type}|{invoice.l10n_gr_edi_project_reference}"}
                }
            # BT-12: ContractDocumentReference
            if invoice.l10n_gr_edi_contract_reference:
                document_node['cac:ContractDocumentReference'] = {
                    'cbc:ID': {'_text': invoice.l10n_gr_edi_contract_reference}
                }
            # BT-122 AdditionalDocumentReference (M.AR.K)
            if invoice.l10n_gr_edi_mark:
                document_node['cac:AdditionalDocumentReference'] = {
                    'cbc:ID': {'_text': str(invoice.l10n_gr_edi_mark)},
                    'cbc:DocumentTypeCode': {'_text': '130'},
                    'cbc:DocumentDescription': {'_text': '##M.AR.K##'},
                }
        # BT-25 Billing reference (preceding invoice number) for credit notes
        elif vals['document_type'] == 'credit_note':
            if invoice.reversed_entry_id:
                document_node['cac:BillingReference'] = {
                    'cac:InvoiceDocumentReference': {
                        'cbc:ID': {'_text': self._format_greek_invoice_number(invoice.reversed_entry_id)},
                    }
                }
        return document_node

    # -------------------------------------------------------------------------
    # Party Nodes (Supplier & Customer)
    # -------------------------------------------------------------------------

    def _ubl_add_party_identification_nodes(self, vals):
        super()._ubl_add_party_identification_nodes(vals)
        partner = vals['party_vals']['partner']
        # BT-46: Contracting authority code (HT code for Greek contracting authorities)
        if partner.id == vals['customer'].id and partner.l10n_gr_edi_contracting_authority_code:
            nodes = vals['party_node']['cac:PartyIdentification']
            nodes.append({
                'cbc:ID': {'_text': partner.l10n_gr_edi_contracting_authority_code}
            })

    # -------------------------------------------------------------------------
    # Line Item Nodes
    # -------------------------------------------------------------------------

    def _add_invoice_line_item_nodes(self, line_node, vals):
        super()._add_invoice_line_item_nodes(line_node, vals)
        line = vals['base_line']['record']
        # BT-158 CPV (Common Procurement Vocabulary) code
        if line and line.product_id:
            cpv_code = line.product_id.l10n_gr_edi_cpv_code
            if cpv_code:
                if 'cac:Item' not in line_node:
                    line_node['cac:Item'] = {}
                if 'cac:CommodityClassification' not in line_node['cac:Item']:
                    line_node['cac:Item']['cac:CommodityClassification'] = []
                line_node['cac:Item']['cac:CommodityClassification'].append({
                    'cbc:ItemClassificationCode': {
                        '_text': cpv_code,
                        'listID': 'CPV'
                    }
                })

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals) or {}
        constraints.update(self._validate_greek_business_rules(invoice))
        return constraints

    def _validate_greek_business_rules(self, invoice):
        """Comprehensive validation of all Greek PEPPOL CIUS business rules"""
        constraints = {}
        vat = invoice.company_id.vat or ''
        buyer_vat = invoice.partner_id.commercial_partner_id.vat
        # GR-R-001-5: Fourth segment - Valid Greek document type
        if not invoice.l10n_gr_edi_inv_type:
            constraints['gr_r_001_5'] = self.env._("Missing Greek Invoice type")
        # GR-R-003: Greek supplier VAT validation
        if not vat.startswith('EL'):
            constraints['gr_r_003'] = self.env._("Supplier VAT must start with 'EL'")
        # GR-R-004: M.AR.K validation
        if not invoice.l10n_gr_edi_mark:
            constraints['gr_r_004_1'] = self.env._("M.AR.K number is required for Suppliers")
        # GR-R-006: Greek buyer VAT validation
        if not buyer_vat or not buyer_vat.startswith('EL'):
            constraints['gr_r_006'] = self.env._("Buyer VAT must start with prefix 'EL'")
        # BT-10 Buyer reference (contracting authority name)
        if not invoice.partner_id.l10n_gr_edi_contracting_authority_name:
            constraints['gr_bt_10'] = self.env._("Contracting authority name is required for Greek buyer")
        # BT-46 (contracting authority code) for Greek buyer
        if not invoice.partner_id.l10n_gr_edi_contracting_authority_code:
            constraints['gr_bt_46'] = self.env._("Contracting authority code is required for Greek buyer")
        # GR-R-007: Project reference validation
        if not invoice.l10n_gr_edi_budget_type or not invoice.l10n_gr_edi_project_reference:
            constraints['gr_r_007'] = self.env._("Budget Type and Project reference is required for B2G invoicing")
        # BT-158: CPV code(KED mandatory fields)
        for line in invoice.invoice_line_ids:
            if line.product_id and not line.l10n_gr_edi_cpv_code:
                constraints['gr_bt_158'] = self.env._(
                    "Each invoice line with a product must have a CPV code for Greek B2G invoicing."
                    "Set CPV code on the product or on the line."
                )
                break
        return constraints

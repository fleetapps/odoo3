from odoo import models


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_ro"

<<<<<<< 258e614605bc313caba1c71642a84bb9787ee6b9
    def _add_invoice_line_item_nodes(self, line_node, vals):
        super()._add_invoice_line_item_nodes(line_node, vals)

        product = vals['base_line']['product_id']
        line_node['cac:Item']['cac:CommodityClassification'] = {
            'cbc:ItemClassificationCode': {
                '_text': product.cpv_code_id.code,
                'listID': 'CPV',
            }
        }
||||||| 0df631380155423e51395612f27943b76b2d1b1c
    def _get_invoice_line_item_vals(self, line, taxes_vals):
        vals = super()._get_invoice_line_item_vals(line, taxes_vals)
        vals['commodity_classification_vals'] = [{
            'item_classification_code': line.product_id.cpv_code_id.code,
            'item_classification_attrs': {'listID': 'CPV'},
        }]
        return vals
=======
    def _get_invoice_line_item_vals(self, line, taxes_vals):
        vals = super()._get_invoice_line_item_vals(line, taxes_vals)
        vals['commodity_classification_vals'] = [{
            'item_classification_code': line.product_id.cpv_code_id.code,
            'item_classification_attrs': {'listID': 'STI'},
        }]
        return vals
>>>>>>> ae92fa1002ce3ab783a60b3c7200d31e37fdb218

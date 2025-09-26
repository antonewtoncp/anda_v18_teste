from odoo import models, fields
from odoo.tools.float_utils import float_round

class AccountTax(models.Model):
    _inherit = "account.tax"

    tax_exigibility = fields.Selection(selection_add=[('withholding', 'Retenção')],string="Exigibilidade da Taxa")
    threshold_wht = fields.Float("Valor Limiar", default=20000,
                                 help="Valor mínimo para o qual a retenção será aplicada")
    exemption_reason = fields.Char(string="Razão de Isenção")
    tax_type = fields.Char(string="Tipo de Taxa")
    tax_code = fields.Char(string="Código da Taxa") 
    
    def _get_tax_details(
        self,
        price_unit,
        quantity,
        precision_rounding=0.01,
        rounding_method='round_per_line',
        product=None,
        special_mode=False,
        **kwargs
    ):
        
        tax_details = super()._get_tax_details(
            price_unit,
            quantity,
            precision_rounding=0.01,
            rounding_method='round_per_line',
            product=None,
            special_mode=False,
            **kwargs 
        )

        for tax_data in tax_details['taxes_data']:
            if tax_data['tax'].tax_exigibility == 'withholding':
                tax_data['tax_amount'] = 0
                
        return tax_details

        
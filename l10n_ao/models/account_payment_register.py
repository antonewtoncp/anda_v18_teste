from odoo import models, fields, api, _


class AccountPayment(models.TransientModel):
    _inherit = "account.payment.register"

    deductible_vat = fields.Monetary(string="Iva Dedutivo")
    deductible_wth = fields.Monetary(string="Retenção Aplicada")

    partner_deductible_vat = fields.Selection(
        [
            ("none", "Não deduz"),
            ("state", "Estado"),
            ("it", "Tecnologia de Informação"),
            ("bank", "Instituição Bancária"),
        ],
        string="Parceiro deduz IVA",
        default="none",
    )

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals["deductible_vat"] = self.deductible_vat
        payment_vals["deductible_wth"] = self.deductible_wth
        payment_vals["partner_deductible_vat"] = self.partner_deductible_vat

        return payment_vals

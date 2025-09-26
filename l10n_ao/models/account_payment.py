from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    deductible_vat = fields.Monetary(string="Iva Dedutivo")
    deductible_wth = fields.Monetary(string="Retenção Aplicada")
    partner_deductible_vat = fields.Selection(
        [
            ("none", "Não deduz"),
            ("state", "Estado"),
            ("it", "Tecnologia de Informação"),
            ("bank", "Instituição Bancária"),
        ],
        string="Parceiro Deduz IVA",
        default="none",
    )

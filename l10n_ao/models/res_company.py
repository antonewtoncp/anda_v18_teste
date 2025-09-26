from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    inv_signed = fields.Boolean("Assinar Faturas", default=True)
    partner_receivable_code_prefix = fields.Char(
        "Prefixo para contas de recebimento de parceiros", size=64, default="31121"
    )
    partner_payable_code_prefix = fields.Char(
        "Prefixo para contas de pagamento de parceiros", size=64, default="32121"
    )
    fpartner_receivable_code_prefix = fields.Char(
        "Prefixo para contas de recebimento de parceiros estrangeiros",
        size=64,
        default="31122",
    )
    fpartner_payable_code_prefix = fields.Char(
        "Prefixo para contas de pagamentos de parceiros estrangeiros",
        size=64,
        default="32122",
    )
    control_account_nature = fields.Boolean(
        string="Controlar Natureza das contas"
    )

    inss = fields.Char("INSS", size=12)
    automatic_partner_account = fields.Boolean(
        string="Criar conta de parceiro automaticamente"
    )

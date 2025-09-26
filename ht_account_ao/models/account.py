from odoo import fields, models, api, _


class AccountCostCenter(models.Model):
    _name = "account.cost.center"
    _description = "Cost Center"

    code = fields.Char(string="Código", required=True)
    name = fields.Char(string="Nome")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda l: l.env.user.company_id,
        string="Empresa",
    )

    _sql_constraints = [
        (
            "cost_center_unique",
            "unique(code)",
            "Já existe um centro de custos com esse código!",
        ),
    ]


class AccountCashFlow(models.Model):
    _name = "account.cash.flow"
    _description = "Fluxo de Caixa"

    code = fields.Char(string="Código", required=True)
    name = fields.Char(string="Nome")

    _sql_constraints = [
        (
            "cash_flow_unique",
            "unique(code)",
            "Já existe um fluxo de caixa com esse código!",
        ),
    ]


class AccountIvaPlan(models.Model):
    _name = "account.iva"
    _description = "IVA Plan"

    code = fields.Char(string="Código", required=True)
    name = fields.Char(string="Nome")
    amount = fields.Float(string="Valor")

    _sql_constraints = [
        (
            "tax_iva_unique",
            "unique(code)",
            "Já existe um plano de IVA com esse código!",
        ),
    ]


class AccountFiscalPlan(models.Model):
    _name = "account.fiscal.plan"
    _description = "Plano Fiscal"

    code = fields.Char(string="Código", required=True)
    name = fields.Char(string="Nome")

    _sql_constraints = [
        (
            "fiscal_plan_unique",
            "unique(code)",
            "Já existe um plano fiscal com esse código!",
        ),
    ]


class AccountAccount(models.Model):
    _inherit = "account.account"

    cost_center = fields.Many2one(
        comodel_name="account.cost.center", string="Centro de Custos"
    )
    cash_flow = fields.Many2one(
        comodel_name="account.cash.flow", string="Fluxo de Caixa"
    )
    iva_plan = fields.Many2one(comodel_name="account.iva", string="Plano de Iva")
    fiscal_plan = fields.Many2one(
        comodel_name="account.fiscal.plan", string="Plano Fiscal"
    )

    has_cost_center = fields.Boolean(string="Usar Centro de custos?")
    has_cash_flow = fields.Boolean(string="Usar Fluxo de Caixa?")
    has_iva = fields.Boolean(string="Usar Plano IVA?")
    has_fiscal_plan = fields.Boolean(string="Usar Plano Fiscal?")

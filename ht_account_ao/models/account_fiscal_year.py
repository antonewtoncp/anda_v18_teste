from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

period_dict = {
    "0": "Abertura",
    "12": "Entradas Ordinárias",
    "13": "Entradas de Regularização",
    "14": "Apuramento",
    "15": "Fecho",
}


class AccountFiscalYear(models.Model):
    _inherit = "account.fiscal.year"
    _description = "Ano Fiscal"

    state = fields.Selection(
        [("open", "Abertura"), ("closed", "Fecho")], string="State", default="open"
    )
    periods = fields.Many2many(comodel_name="account.fiscal.period", string="Período")

    @api.model
    def create(self, vals):
        result = super(AccountFiscalYear, self).create(vals)
        for rec in ["0", "12", "13", "14", "15"]:
            self.ordinary_entries(result, rec)
        period = self.env["account.fiscal.period"].search([("year", "=", result.id)])
        result.periods |= period
        return result

    def unlink(self):
        for res in self:
            moves = self.env["account.move"].search([("year", "=", res.id)])
            period = self.env["account.fiscal.period"].search([("year", "=", res.id)])
            for rec in period:
                rec.unlink()
            if moves:
                raise ValidationError("Impossível eliminar Ano Fiscal com movimentos")
        super(AccountFiscalYear, self).unlink()

    def write(self, vals):
        for res in self:
            if vals.get("periods"):
                if vals.get("periods")[0][2]:
                    for period_model in res.periods:
                        if period_model.id not in vals.get("periods")[0][2]:
                            moves = self.env["account.move"].search(
                                [("period", "=", period_model.id)]
                            )
                            if moves:
                                raise ValidationError(
                                    "Impossível eliminar Período com movimentos"
                                )
                else:
                    for period_model in res.periods:
                        moves = self.env["account.move"].search(
                            [("period", "=", period_model.id)]
                        )
                        if moves:
                            raise ValidationError(
                                "Impossível eliminar Período com movimentos"
                            )
        super(AccountFiscalYear, self).write(vals)

    def ordinary_entries(self, year_model, period):
        """
        normal entries of account move
        :param year_model:
        :return:
        """
        period = self.env["account.fiscal.period"].create(
            {
                "year": year_model.id,
                "start_date": year_model.date_from,
                "end_date": year_model.date_to,
                "period": period,
                "company_id": year_model.company_id.id,
            }
        )
        return period

    def button_close(self):
        self.state = "closed"


class AccountFiscalPeriod(models.Model):
    _name = "account.fiscal.period"
    _description = "Período Fiscal"

    name = fields.Char(string="Nome", compute="_compute_name")
    start_date = fields.Date(string="Data de Inicio")
    end_date = fields.Date(string="Data de Fim")
    period = fields.Selection(
        [
            ("0", "Abertura"),
            ("12", "Entradas Ordinárias"),
            ("13", "Entradas de Regularização"),
            ("14", "Apuramento"),
            ("15", "Fecho"),
        ],
        string="Período",
    )
    year = fields.Many2one(comodel_name="account.fiscal.year", string="Ano Fiscal")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda l: l.env.user.company_id,
        string="Empresa",
    )

    def unlink(self):
        for res in self:
            moves = self.env["account.move"].search([("period", "=", res.id)])
            if moves:
                raise ValidationError("Impossível eliminar Período com movimentos")
        super(AccountFiscalPeriod, self).unlink()

    @api.depends("period")
    def _compute_name(self):
        for res in self:
            res.name = period_dict[res.period]

    @api.constrains("start_date")
    def validate_date(self):
        if self.start_date > self.end_date:
            raise ValidationError("A data de inicio deve ser menor que a data de fim")


class Setup(models.TransientModel):
    _inherit = "account.financial.year.op"

    year = fields.Many2one(
        related="company_id.accounting_year", required=1, readonly=False
    )

    @api.onchange("year")
    def onchange_year(self):
        if self.year:
            self.opening_date = self.year.date_from
            self.fiscalyear_last_day = self.year.date_to.day
            self.fiscalyear_last_month = str(self.year.date_to.month)

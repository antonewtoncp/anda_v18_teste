from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang
from typing import List, Union
from datetime import date
import time


class AccountDemoNat(models.TransientModel):
    _name = "account.demonstration"
    _description = "Report Model for balance"
    _rec_name = "company_id"

    accounting_year = fields.Many2one(
        comodel_name="account.fiscal.year", string="Fiscal Year"
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        string="Empresa",
    )
    accountent = fields.Char(string="Contabilista")

    manager = fields.Char(string="Gestor")

    date_from = fields.Date(string="Data de Início")

    date_to = fields.Date(string="Date de Fim")

    enable_filter = fields.Boolean(string="Fazer Comparação", default=False)

    type = fields.Selection(
        [("nature", "NATURE"), ("function", "FUNCTION")],
        string="Type",
        default="nature",
    )

    target_move = fields.Selection(
        [
            ("posted", "Todas as entradas publicadas"),
            ("all", "Todas as entradas"),
        ],
        default="posted",
        string="Movimentos Contabilísticos Específicos",
    )

    accounts = fields.Many2many("account.account", string="Accounts")
    accounts_move_line = fields.Many2many(
        "account.move.line", string="Accounts Move Line"
    )

    @api.model
    def load_data_accounts(self):
        # Cria um dicionário para armazenar a contagem de lançamentos por conta
        account_counts = {}

        # Busca todas as linhas de movimento
        move_lines = self.env["account.move.line"].read_group(
            [("account_id", "!=", False)], ["account_id"], ["account_id"]
        )

        for move_line in move_lines:
            account_id = move_line["account_id"][0]
            count = move_line["account_id_count"]
            if count >= 1:
                account_counts[account_id] = count

        """Busca todas as contas no modelo 'account.account'."""
        # Busca todas as contas financeiras no sistema
        accounts = self.env["account.account"].browse(account_counts.keys())

        for account in accounts:
            print(f"Code - {account.code}")
        # Retorna os IDs das contas
        return [(6, 0, accounts.ids)]

    @api.model
    def load_data_accounts_move_line(self, accounts):
        """Busca todas as contas no modelo 'account.account'."""
        # Busca todas as contas financeiras no sistema
        accounts_move_line = self.env["account.move.line"].search(
            [("account_id", "in", accounts[0][2]), ("move_id.state", "=", "posted")]
        )
        for movee in accounts_move_line:
            print(f"Code - {movee.account_id.code} - {movee.balance}")
        # Retorna os IDs das contas
        return [(6, 0, accounts_move_line.ids)]

    def default_get(self, fields):
        """Sobrescreve o default_get para carregar os dados automaticamente."""
        res = super(AccountDemoNat, self).default_get(fields)
        # Chama o método para carregar as contas
        accounts = self.load_data_accounts()
        res["accounts"] = accounts
        res["accounts_move_line"] = self.load_data_accounts_move_line(accounts)
        return res

    def get_periods(self):
        ordinary_period = self.env['account.fiscal.period'].search([
            ('start_date', '=', self.date_from),
            ('period', '=', 12),
            ('company_id', '=', self.company_id.id)
        ])
        regularizaction = self.env['account.fiscal.period'].search([
            ('start_date', '=', self.date_from),
            ('period', '=', 13),
            ('company_id', '=', self.company_id.id)
        ])
        return ordinary_period.id, regularizaction.id

    def get_all_period(self):
        all_period = []
        open_period = self.env['account.fiscal.period'].search([
            ('start_date', '=', self.date_from),
            ('period', 'in', [0, 12, 13, 14, 15]),
            ('company_id', '=', self.company_id.id)
        ])
        for period in open_period:
            all_period.append(period.id)
        return all_period

    def get_account_balance(self, codes: Union[List[str], str], date_from: date, date_to: date) -> float:
        ordinary_period, regularizaction = self.get_periods()
        query = """
            SELECT SUM(balance) as total_balance
            FROM account_move_line aml
            INNER JOIN account_account aa ON aml.account_id = aa.id
            INNER JOIN account_move am ON aml.move_id = am.id
            WHERE aml.date >= %s AND aml.date <= %s
            AND aml.company_id = %s
            AND (aml.period = %s OR aml.period = %s OR aml.period NOT IN %s)
            
        """
        all_periods = tuple(self.get_all_period())
        params = [date_from, date_to, self.company_id.id, ordinary_period, regularizaction, all_periods]

        if isinstance(codes, list):
            if not codes:
                return 0.0
            codes_like = " OR ".join(["aml.account_code LIKE %s" for _ in codes])
            query += f" AND ({codes_like})"
            params.extend([f"{code}%" for code in codes])
        else:
            query += " AND aml.account_code LIKE %s"
            params.append(f"{codes}%")

        if self.target_move == 'posted':
            query += " AND am.state = 'posted'"

        self.env.cr.execute(query, tuple(params))
        result = self.env.cr.fetchone()

        return result[0] if result[0] is not None else 0.0

    # def get_account_balance(self, code, date_from: date, date_to: date) -> float:
    #     codes = str(code)
    #     account_sum_values = []
    #     for move in self.accounts_move_line:
    #         if self.date_from <= move.date <= self.date_to:
    #             if len(codes) == 2:
    #                 if move.account_id.code[:2] == codes[:2]:
    #                     sum_move_line_code = move.balance
    #                     account_sum_values.append(sum_move_line_code)
    #             else:
    #                 if move.account_id.code[:3] == codes[:3]:
    #                     sum_move_line_code = move.balance
    #                     account_sum_values.append(sum_move_line_code)
    #     sum_move_line_code = abs(round(sum(values for values in account_sum_values), 2))
    #     return sum_move_line_code

    def get_account_balance_previous_years(self, code) -> float:
        codes = str(code)
        account_sum_values = []
        prev_date_to = self.date_to.replace(self.date_to.year - 1)
        prev_date_from = self.date_from.replace(self.date_to.year - 1)
        for move in self.accounts_move_line:
            if prev_date_from <= move.date <= prev_date_to:
                if len(codes) == 2:
                    if move.account_id.code[:2] == codes[:2]:
                        sum_move_line_code = move.balance
                        account_sum_values.append(sum_move_line_code)
                else:
                    if move.account_id.code[:3] == codes[:3]:
                        sum_move_line_code = move.balance
                        account_sum_values.append(sum_move_line_code)
        sum_move_line_code = abs(round(sum(values for values in account_sum_values), 2))
        return sum_move_line_code

    def get_accounts_balances(self, codes: List[int]) -> float:
        sum_account = round(sum(self.get_account_balance(code) for code in codes), 2)
        return sum_account

    @api.onchange("accounting_year")
    def onchange_accounting_year(self):
        self.date_from = self.accounting_year.date_from
        self.date_to = self.accounting_year.date_to

    def print(self):
        if self.type == "function":
            return self.env.ref(
                "cp_account_report_ao.action_account_demonstration_fun_report"
            ).report_action(self)
        return self.env.ref(
            "cp_account_report_ao.action_account_demonstration_nat_report"
        ).report_action(self)

    def prev_accounting_year(self):
        prev_accounting_year = self.env["account.fiscal.year"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("name", "=", str(int(self.accounting_year.name) - 1)),
            ]
        )
        if prev_accounting_year:
            return prev_accounting_year[0]

    def format(self, value):
        return formatLang(self.env, value, currency_obj=self.company_id.currency_id)

    @api.constrains("enable_filter")
    def _check_prev_accounting_year(self):
        for record in self:
            if record.enable_filter and not record.prev_accounting_year():
                raise ValidationError(
                    "Não pode Fazer Comparação Porque não existe um ano fiscal anterior a este .\n "
                    "Certifique-se de que o ano fiscal  anterior foi criado e tente novamente"
                )

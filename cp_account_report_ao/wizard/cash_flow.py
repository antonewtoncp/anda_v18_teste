from datetime import date
from typing import List, Union

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang


class AccountDemoNat(models.TransientModel):
    _name = "cash.flow"
    _description = "Report Model for cash flow"
    _rec_name = "company_id"

    accounting_year = fields.Many2one(
        comodel_name="account.fiscal.year", string="Ano Fiscal"
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        string="Empresa",
    )

    accountent = fields.Char(string="Contabilista")
    manager = fields.Char(string="Gestor ")

    date_from = fields.Date(string="Data de Início")

    date_to = fields.Date(string="Date de Fim")

    enable_filter = fields.Boolean(string="Fazer Comparação", default=False)

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

    @api.model
    def default_get(self, fields):
        """Sobrescreve o default_get para carregar os dados automaticamente."""
        res = super(AccountDemoNat, self).default_get(fields)
        # Chama o método para carregar as contas
        accounts = self.load_data_accounts()
        res["accounts"] = accounts
        res["accounts_move_line"] = self.load_data_accounts_move_line(accounts)
        return res

    def get_account_balance(self, code) -> float:
        codes = str(code)
        account_sum_values = []
        for move in self.accounts_move_line:
            if self.date_from <= move.date <= self.date_to:
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
        if not self.enable_filter:
            sum_account = round(
                sum(self.get_account_balance(code) for code in codes), 2
            )
        else:
            sum_account = round(
                sum(self.get_account_balance_previous_years(code) for code in codes), 2
            )
        return sum_account

    @api.onchange("accounting_year")
    def onchange_accounting_year(self):
        self.date_from = self.accounting_year.date_from
        self.date_to = self.accounting_year.date_to

    def print(self):
        return self.env.ref("cp_account_report_ao.action_cash_flow_dir").report_action(
            self
        )

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

    # def get_account_balance(self, codes, date_from, date_to):
    #     domain = [
    #         ('date', '>=', date_from),
    #         ('date', '<=', date_to),
    #     ]
    #
    #     if isinstance(codes, list):
    #         for code in codes:
    #             domain.append(('account_id.code', '=like', f'{code}%'))
    #     else:
    #         domain.append(('account_id.code', '=like', f'{codes}%'))
    #
    #     if self.target_move == 'posted':
    #         domain.append(('move_id.state', '=', 'posted'))
    #
    #     return sum(self.env['account.move.line'].search(domain).mapped('balance'))

from typing import List, Union

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang
from typing import List, Union
from datetime import date
from datetime import datetime
from datetime import date



class AccountFinaBalance(models.TransientModel):
    _name = "account.financial.balance"
    _description = "Report Model for balance"

    accounting_year = fields.Many2one(
        comodel_name="account.fiscal.year", string="Ano Fiscal"
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        string="empresa",
    )

    accountent = fields.Char(string="Contabilista")

    manager = fields.Char(string=" Gestor ")

    date_from = fields.Date(string="Data de Início")
    date_to = fields.Date(string="Date de Fim")

    enable_filter = fields.Boolean(string="Fazer Comparação", default=False)

    target_move = fields.Selection(
        [
            ("posted", "Todas as entradas Postadas"),
            ("all", "Todas as entradas"),
        ],
        default="posted",
        string="Movimentos Contabilísticos Específicos",
    )

    accounts = fields.Many2many("account.account", string="Accounts")
    accounts_move_line = fields.Many2many(
        "account.move.line", string="Accounts Move Line"
    )

    opened = fields.Boolean(string="Abertura Automática", default=True)

    # prev_accounting_year = fields.Many2one(
    #     comodel_name='account.fiscal.year', string="Ano Fiscal Anterior")
    @api.onchange("accounting_year")
    def onchange_accounting_year(self):
        self.date_from = self.accounting_year.date_from
        self.date_to = self.accounting_year.date_to

    def print(self):
        return self.env.ref(
            "cp_account_report_ao.action_account_financial_balance"
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
        res = super(AccountFinaBalance, self).default_get(fields)
        # Chama o método para carregar as contas
        accounts = self.load_data_accounts()
        res["accounts"] = accounts
        res["accounts_move_line"] = self.load_data_accounts_move_line(accounts)
        return res

    def get_date_to_befor(self):
        date_to_before = self.date_to
        if self.opened:
            actual_date_to = self.date_to
            date_to_before = actual_date_to.replace(year=actual_date_to.year - 1)
        return date_to_before
    
    def get_date_from_befor(self):
        date_from_before = self.date_from
        date_from_before = date_from_before.replace(year=date_from_before.year - 1)
        return date_from_before

    def get_first_fiscal_year(self):
        min_date = self.date_from
        if self.opened:
            actual_date_from = self.date_from
            actual_date_to = self.date_to
            min_date = actual_date_from.replace(year=actual_date_to.year - 1)

        previous_date_from = min_date    
        return previous_date_from

    def get_date_before_before(self):
        date_to_before = self.get_first_fiscal_year()
        if self.opened:
            actual_date_to = self.date_to
            date_to_before = actual_date_to.replace(year=actual_date_to.year - 2)
        return date_to_before

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

    def get_account_balance_per_period(self, codes: Union[List[str], str], date_from: date, date_to: date) -> float:
        all_periods = tuple(self.get_all_period())
        if not isinstance(codes, (list, tuple)):  
            codes = [codes]

        if '34' in map(str, codes):
            min_year = self.env['account.fiscal.year'].search([('company_id', '=', self.company_id.id)]).mapped('date_from')
            if min_year:
                min_year = min(min_year).year
                min_date = datetime.strptime(f'{min_year}-01-01', '%Y-%m-%d').date()
                
            if min_date > date_from:
                ordinary_period = self.env['account.fiscal.period'].search([
                    ('start_date', '=', self.date_from),
                    ('period', '=', 12),
                    ('company_id', '=', self.company_id.id)
                ],limit=1)
                regularizaction = self.env['account.fiscal.period'].search([
                    ('start_date', '=', self.date_from),
                    ('period', '=', 13),
                    ('company_id', '=', self.company_id.id)
                ],limit=1)

                query = """
                    SELECT SUM(balance) as total_balance
                    FROM account_move_line aml
                    INNER JOIN account_account aa ON aml.account_id = aa.id
                    INNER JOIN account_move am ON aml.move_id = am.id
                    WHERE aml.date >= %s AND aml.date <= %s
                    AND aml.company_id = %s
                    AND ((aml.period = %s OR aml.period = %s))
                    
                """
                params = [self.date_from, self.date_to, self.company_id.id, ordinary_period.id or -1, regularizaction.id or -1]
            else:
                ordinary_period = self.env['account.fiscal.period'].search([
                    ('start_date', '=', self.date_from),
                    ('period', '=', 12),
                    ('company_id', '=', self.company_id.id)
                ],limit=1)
                regularizaction = self.env['account.fiscal.period'].search([
                    ('start_date', '=', self.date_from),
                    ('period', '=', 13),
                    ('company_id', '=', self.company_id.id)
                ],limit=1)
                query = """
                    SELECT SUM(balance) as total_balance
                    FROM account_move_line aml
                    INNER JOIN account_account aa ON aml.account_id = aa.id
                    INNER JOIN account_move am ON aml.move_id = am.id
                    WHERE aml.company_id = %s AND (((aml.date >= %s AND aml.date <= %s) AND (aml.period = %s OR aml.period = %s OR aml.period NOT IN %s))
                    OR (aml.date < %s ))
                                        
                """                
                params = [self.company_id.id, self.date_from, self.date_to, ordinary_period.id or 1, regularizaction.id or 1, all_periods, self.date_from]
        else:
            ordinary_period = self.env['account.fiscal.period'].search([
                ('start_date', '=', date_from),
                ('period', '=', 12),
                ('company_id', '=', self.company_id.id)
            ],limit=1)
            regularizaction = self.env['account.fiscal.period'].search([
                ('start_date', '=', date_from),
                ('period', '=', 13),
                ('company_id', '=', self.company_id.id)
            ],limit=1)

            query = """
                SELECT SUM(balance) as total_balance
                FROM account_move_line aml
                INNER JOIN account_account aa ON aml.account_id = aa.id
                INNER JOIN account_move am ON aml.move_id = am.id
                WHERE aml.date >= %s AND aml.date <= %s
                AND aml.company_id = %s
                AND ((aml.period = %s OR aml.period = %s OR aml.period NOT IN %s) OR (aml.date < %s))
                
            """

            params = [date_from, date_to, self.company_id.id, ordinary_period.id or -1, regularizaction.id or -1, all_periods, self.date_from]

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


    # def get_account_balance(self, code) -> float:
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
    def get_account_balance(self, codes: Union[List[str], str], date_from: date, date_to: date) -> float:
        
        query = """
            SELECT SUM(balance) as total_balance
            FROM account_move_line aml
            INNER JOIN account_account aa ON aml.account_id = aa.id
            INNER JOIN account_move am ON aml.move_id = am.id
            WHERE aml.date >= %s AND aml.date <= %s
            AND aml.company_id = %s
        """

        params = [date_from, date_to, self.company_id.id]

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

    # def get_account_balance(self, codes: Union[List[str], str], date_from: date, date_to: date) -> float:
        
    #     query = """
    #         SELECT SUM(balance) as total_balance
    #         FROM account_move_line aml
    #         INNER JOIN account_account aa ON aml.account_id = aa.id
    #         INNER JOIN account_move am ON aml.move_id = am.id
    #         WHERE aml.date >= %s AND aml.date <= %s
    #         AND aml.company_id = %s
    #     """

    #     params = [date_from, date_to, self.company_id.id]

    #     if isinstance(codes, list):
    #         if not codes:
    #             return 0.0
    #         codes_like = " OR ".join(["aa.account_code LIKE %s" for _ in codes])
    #         query += f" AND ({codes_like})"
    #         params.extend([f"{code}%" for code in codes])
    #     else:
    #         query += " AND aa.account_code LIKE %s"
    #         params.append(f"{codes}%")

    #     if self.target_move == 'posted':
    #         query += " AND am.state = 'posted'"

    #     self.env.cr.execute(query, tuple(params))
    #     result = self.env.cr.fetchone()

    #     return result[0] if result[0] is not None else 0.0

    @api.constrains("enable_filter")
    def _check_prev_accounting_year(self):
        for record in self:
            if record.enable_filter and not record.prev_accounting_year():
                raise ValidationError(
                    "Não pode Fazer Comparação Porque não existe um ano fiscal anterior a este .\n "
                    "Certifique-se de que o ano fiscal  anterior foi criado e tente novamente"
                )

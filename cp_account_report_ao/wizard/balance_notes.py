from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang
from typing import List, Union
from datetime import date


class BanceNotes(models.TransientModel):
    _name = "balance.notes.wizard"
    _description = "Report Model for Notes to Balance"
    _rec_name = "company_id"

    accounting_year = fields.Many2one(
        comodel_name="account.fiscal.year", string="Ano Fiscal"
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        string="Empresa",
    )

    date_from = fields.Date(string="Data de Início")

    date_to = fields.Date(string="Date de Fim")

    enable_filter = fields.Boolean(string="Fazer Comparação", default=False)

    type = fields.Selection(
        [("balance", "Notas ao Balanço"), ("demon", "Notas a Demonstração ")],
        string="Tipo",
        default="balance",
    )
    opened = fields.Boolean(string="Abertura Automática", default=True)

    target_move = fields.Selection(
        [
            ("posted", "Todas as entradas publicadas"),
            ("all", "Todas as entradas"),
        ],
        default="posted",
        string="Movimentos Contabilísticos Específicos",
    )

    @api.onchange("accounting_year")
    def onchange_accounting_year(self):
        self.date_from = self.accounting_year.date_from
        self.date_to = self.accounting_year.date_to

    def print(self):
        if self.type == "balance":
            return self.env.ref(
                "cp_account_report_ao.action_balance_notes_report"
            ).report_action(self)
        return self.env.ref(
            "cp_account_report_ao.action_demon_notes_report"
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
    
    def get_date_from_befor(self):
        date_from_before = self.date_from
        date_from_before = date_from_before.replace(year=date_from_before.year - 1)
        return date_from_before

    def get_account_balance(
        self, codes: Union[List[str], str], date_from: date, date_to: date
    ) -> float:

        query = """
            SELECT SUM(balance) as total_balance
            FROM account_move_line aml
            INNER JOIN account_account aa ON aml.account_id = aa.id
            INNER JOIN account_move am ON aml.move_id = am.id
            WHERE aml.date >= %s AND aml.date <= %s
        """
        params = [date_from, date_to]

        if isinstance(codes, list):
            if not codes:
                return 0.0
            codes_like = " OR ".join(["aml.account_code LIKE %s" for _ in codes])
            query += f" AND ({codes_like})"
            params.extend([f"{code}%" for code in codes])
        else:
            query += " AND aml.account_code LIKE %s"
            params.append(f"{codes}%")

        if self.target_move == "posted":
            query += " AND am.state = 'posted'"

        self.env.cr.execute(query, tuple(params))
        result = self.env.cr.fetchone()

        return result[0] if result[0] is not None else 0.0
    
    def get_account_balance2(self, codes: Union[List[str], str], date_from: date, date_to: date) -> float:
        period_id = self.env['account.fiscal.period'].search([
                ('start_date', '=', date_from), 
                ('company_id', '=', self.company_id.id),
                ('period', '=', 12)
                ])
        
        query = """
            SELECT SUM(balance) as total_balance
            FROM account_move_line aml
            INNER JOIN account_account aa ON aml.account_id = aa.id
            INNER JOIN account_move am ON aml.move_id = am.id
            AND aml.date >= %s AND aml.date <= %s
            AND aml.company_id = %s
            AND aml.period = %s
        """
        if self.opened:
            params = [self.get_date_from_befor(), date_to, self.company_id.id, period_id.id]
        else:
            params = [date_from, date_to, self.company_id.id, period_id.id]
            # print("TESTE2: ",List, " ----- DATA INICIAL2: ",date_from, " --- DATA FINAL2: ",date_to, " PERID: ",period_id.name)
            
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
        
        # print("Eus osu periodo: ", self.period)
        
        # periods = self.env['account.move'].search([('period', '!=', False)]).mapped('period.name')
        # print("Eus osu periodo: ", periods, " e ano atual é: ",ano_atual)
        # self.get_regularization_period_ordinary()

        return result[0] if result[0] is not None else 0.0
    
    def get_account_balance_clearance(self, codes: Union[List[str], str], date_from: date, date_to: date) -> float:
        period_id = self.env['account.fiscal.period'].search([
                ('start_date', '=', date_from), 
                ('company_id', '=', self.company_id.id),
                ('period', '=', 14)
                ], limit=1)
        
        query = """
            SELECT SUM(balance) as total_balance
            FROM account_move_line aml
            INNER JOIN account_account aa ON aml.account_id = aa.id
            INNER JOIN account_move am ON aml.move_id = am.id
            AND aml.date >= %s AND aml.date <= %s
            AND aml.company_id = %s
            AND aml.period = %s
        """
        if self.opened:
            params = [self.get_date_from_befor(), date_to, self.company_id.id, period_id.id]
        else:
            params = [date_from, date_to, self.company_id.id, period_id.id]
            # print("TESTE2: ",List, " ----- DATA INICIAL2: ",date_from, " --- DATA FINAL2: ",date_to, " PERID: ",period_id.name)
            
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
        
        # print("Eus osu periodo: ", self.period)
        
        # periods = self.env['account.move'].search([('period', '!=', False)]).mapped('period.name')
        # print("Eus osu periodo: ", periods, " e ano atual é: ",ano_atual)
        # self.get_regularization_period_ordinary()

        return result[0] if result[0] is not None else 0.0
    

    @api.constrains("enable_filter")
    def _check_prev_accounting_year(self):
        for record in self:
            if record.enable_filter and not record.prev_accounting_year():
                raise ValidationError(
                    "Não pode Fazer Comparação Porque não existe um ano fiscal anterior a este .\n "
                    "Certifique-se de que o ano fiscal  anterior foi criado e tente novamente"
                )

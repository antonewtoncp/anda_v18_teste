# -*- coding: utf-8 -*-
#############################################################################
#
#    Compplexus smart soluction . Ltd.
#
#    Copyright (C) 2024-TODAY Compplexus smart soluction(<https://www.compllexus.com>)
#    Author: Compplexus  ((<https://www.compllexus.com>v)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#
#
#############################################################################
from odoo import fields, models

selection_field = {"posted": "Posted Entries only", "draft": "Include UnPosted Entries"}


class GeneralContab(models.TransientModel):
    """Create new model"""

    _name = "general.contability.report"
    _description = "Report Model for General contability"

    accounting_year = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Ano Fiscal",
        default=lambda self: self.env.user.company_id.accounting_year,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        string="Empresa",
    )

    start_date = fields.Date(
        string="Data de Início",
        related="accounting_year.date_from",
        help="Select start date" "to fetch the trial balance data",
    )

    end_date = fields.Date(
        string="Data de Fim",
        related="accounting_year.date_to",
        help="Select end date " "to fetch the trial balance data",
    )

    journals_ids = fields.Many2many(
        "account.journal",
        string="Diário",
        help="Select the journals to added in the" "trail balance",
    )
    state = fields.Selection(
        [
            ("draft", "Rascunho (não Postadas) "),
            ("posted", "Postados"),
        ],
        tracking=True,
        default="posted",
        string="Estado",
        help="Select the state of journal " "entries which we want to report",
    )

    def button_to_get_pdf(self):
        """It will create the report using defined query"""
        where_conditions = []
        parameters = []
        state_value = ""
        currency = self.env.user.company_id.currency_id.symbol
        if self.start_date:
            where_conditions.append("account_move_line.date >= %s")
            parameters.append(self.start_date)
        if self.end_date:
            where_conditions.append("account_move_line.date <= %s")
            parameters.append(self.end_date)
        if self.company_id:
            where_conditions.append("account_move_line.company_id = %s")
            parameters.append(str(self.company_id.id))
        if self.state == "posted":
            where_conditions.append("parent_state = 'posted'")
        if self.state == "draft":
            where_conditions.append("parent_state in ('posted', 'draft')")
        if self.journals_ids:
            journal_ids = [journal.id for journal in self.journals_ids]
            where_conditions.append("journal_id IN %s")
            parameters.append(tuple(journal_ids))
        where_query = " AND ".join(where_conditions)
        query = """
            SELECT
                account_code AS code,
                account_account.name AS ac_name,
                SUM(account_move_line.debit) AS debit,
                SUM(account_move_line.credit) AS credit,
                SUM(account_move_line.debit) - SUM(account_move_line.credit) AS 
                balance
            FROM
                account_move_line
            JOIN
                account_account ON account_account.id = 
                account_move_line.account_id
            {}
            GROUP BY
                account_id,
                account_account.name,
                account_code
        """.format(
            "WHERE " + where_query if where_conditions else ""
        )
        self.env.cr.execute(query, tuple(parameters))
        main_query = self.env.cr.dictfetchall()
        total_credit = 0.0
        total_debit = 0.0
        for rec in main_query:
            total_credit += rec["credit"]
            total_debit += rec["debit"]
        balance = total_debit - total_credit
        if self.state:
            state_value = selection_field[self.state]
        journals = str(self.journals_ids.mapped("name"))
        result = journals[1:-1].replace("'", "")
        data = {
            "query": main_query,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_credit": round(total_credit, 2),
            "total_debit": round(total_debit, 2),
            "balance": round(balance),
            "currency": currency,
            "state": state_value,
            "journals_name": result,
        }
        return self.env.ref(
            "cp_account_report_ao.action_contability_report_ao"
        ).report_action(self, data=data)

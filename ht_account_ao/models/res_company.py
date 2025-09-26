from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    # tax_withhold_journal_id = fields.Many2one('account.journal', 'Withhold Journal')
    # tax_withhold_received_account_id = fields.Many2one('account.account', 'DAR Received Account')
    # tax_withhold_sent_account_id = fields.Many2one('account.account', "DAR Sent Account")

    invoice_cost_center = fields.Boolean(string="Centro de Custos para Faturação")

    accounting_year = fields.Many2one(
        comodel_name="account.fiscal.year", string="Ano Fiscal", required=False
    )
    account_opening_date = fields.Date(
        string="Data de Abertura do Ano Fiscal",
        related="accounting_year.date_from",
        required=True,
        help="Está é a data de abertura do ano fiscal",
    )

    @api.model
    def create_op_move_if_non_existant(self):
        """Creates an empty opening move in 'draft' state for the current company
        if there wasn't already one defined. For this, the function needs at least
        one journal of type 'general' to exist (required by account.move).
        """
        self.ensure_one()
        if not self.account_opening_move_id:
            default_journal = self.env["account.journal"].search(
                [("type", "=", "general"), ("company_id", "=", self.id)], limit=1
            )

            if not default_journal:
                raise UserError(
                    "Por favor instale um plano de contas ou crie um diário geral antes de prosseguir."
                )

            if not self.account_opening_date:
                self.account_opening_date = fields.Date.context_today(self).replace(
                    month=1, day=1
                )
            opening_date = self.account_opening_date - timedelta(days=1)

            self.account_opening_move_id = self.env["account.move"].create(
                {
                    "ref": "Entrada de Abertura do diário",
                    "company_id": self.id,
                    "journal_id": default_journal.id,
                    "date": opening_date,
                }
            )

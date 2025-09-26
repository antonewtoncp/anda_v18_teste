from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_total_wth = fields.Monetary(
        string="Total com Retenção", readonly=True, compute="_compute_wth_values"
    )
    amount_wth_apply = fields.Monetary(
        string="Valor por Reter", readonly=True, compute="_compute_wth_values"
    )

    @api.depends("line_ids.tax_ids")
    def _compute_wth_values(self):
        for record in self:
            wth_apply = 0
            for line in record.line_ids:
                withholding_taxes = line.tax_ids.filtered(
                    lambda tax: tax.tax_exigibility == "withholding"
                )

                for tax in withholding_taxes:
                    wth_apply += line.price_subtotal * (tax.amount / 100)

            record.amount_wth_apply = wth_apply
            record.amount_total_wth = record.amount_total - wth_apply

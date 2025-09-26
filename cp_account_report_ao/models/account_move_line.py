from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    reason_code = fields.Char(
        string="Reason Code", compute="_account_code", store=True, pre_compute=True
    )
    integrator_code = fields.Char(
        string="Integrator Code", compute="_account_code", store=True, pre_compute=True
    )
    account_code = fields.Char(
        string="Account Code", compute="_account_code", store=True
    )
    move_id_state = fields.Selection(
        related="move_id.state", string="state", store=True, pre_compute=True
    )

    @api.depends(
        "account_id.reason_code", "account_id.integrator_code", "account_id.code"
    )
    def _account_code(self):
        for res in self:
            res.reason_code = res.account_id.reason_code
            res.integrator_code = res.account_id.integrator_code
            res.account_code = res.account_id.code


class AccountMoveAssets(models.Model):
    _inherit = "account.move"

    amount_assets_amortization = fields.Integer(
        string="Amount Amortization", compute="_compute_amount_amortization"
    )

    @api.depends("asset_id", "date")
    def _compute_amount_amortization(self):
        for rec in self:
            if rec.asset_id:
                if rec.date > fields.Date().today():
                    rec.amount_assets_amortization = 0.0
                else:
                    rec.amount_assets_amortization = (
                        rec.asset_id.original_value * rec.asset_id.tax
                    ) / 100.0
            else:
                rec.amount_assets_amortization = 0.0

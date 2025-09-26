from odoo import fields, models, api, _


class AOAccountConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    automatic_partner_account = fields.Boolean(
        related="company_id.automatic_partner_account", readonly=False
    )
    control_account_nature = fields.Boolean(
        related="company_id.control_account_nature", readonly=False
    )
    inv_signed = fields.Boolean(related="company_id.inv_signed", readonly=False)
    partner_receivable_code_prefix = fields.Char(
        related="company_id.partner_receivable_code_prefix", readonly=False
    )
    partner_payable_code_prefix = fields.Char(
        related="company_id.partner_payable_code_prefix", readonly=False
    )
    fpartner_receivable_code_prefix = fields.Char(
        related="company_id.fpartner_receivable_code_prefix", readonly=False
    )
    fpartner_payable_code_prefix = fields.Char(
        related="company_id.fpartner_payable_code_prefix", readonly=False
    )
from odoo import api, models, fields, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    purchase_cost_center = fields.Boolean(string="Purchase Cost Center")

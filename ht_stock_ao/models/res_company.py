from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    stock_cost_center = fields.Boolean(string="Centro de Custos para Inventário?")

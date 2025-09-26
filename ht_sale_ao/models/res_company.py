from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_cost_center = fields.Boolean(string="Centro de Custos para Vendas")

from odoo import fields, models, api, _


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda l: l.env.user.company_id)

    @api.model
    def _get_default_rule_ids(self):
        return [

        ]

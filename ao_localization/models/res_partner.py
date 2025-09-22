"""
@autor: Compllexus
"""

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _default_county(self):
        return self.env['res.country.state.county'].sudo().search([('code', '=', 'LDA')]).id

    county_id = fields.Many2one("res.country.state.county", string="County", default=_default_county)

    @api.onchange('state_id')
    def _onchange_state_id_id(self):
        if self.state_id:
            return {'domain': {'county_id': [('state_id', '=', self.state_id.id)]}}
        else:
            return {'domain': {'county_id': []}}

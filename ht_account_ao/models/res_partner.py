from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _default_country(self):
        return self.env.ref("base.ao")

    country_id = fields.Many2one(
        "res.country", string="País", ondelete="restrict", default=_default_country
    )
    state_id = fields.Many2one(
        "res.country.state",
        string="Província",
        ondelete="restrict",
    )
    city = fields.Char(default="Luanda")
    sector = fields.Selection(
        [("public", "Sector Publico"), ("private", "Sector Privado")], default="private"
    )
    # iva_cativo = fields.Selection(
    #     [('yes', 'Cativa IVA'), ('no', 'Não Cativa IVA')],default="no"
    # )
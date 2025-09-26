from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    tax_entity = fields.Char("Entity")
    agt_cert_number = fields.Char(
        "Software Validation Number", readonly=True, default="447/AGT/2023"
    )
    software_validation_number = fields.Char(
        "Software Validation Number", readonly=True, default="Compllexus_Odoo"
    )
    agt_product_name = fields.Char(
        "Product ID", readonly=True, default="Compllexus_Odoo"
    )
    agt_product_version = fields.Char("Product Version", readonly=True, default="17.0")
    product_version = fields.Char("Product Version", readonly=True, default="17.0")

    audit_file_version = fields.Char(
        "Audit File Version", readonly=True, default="1.01_01"
    )
    key_version = fields.Char(string="Key Version", default="1")
    product_company_name = fields.Char(
        "Product Company Name",
        readonly=True,
        default="COMPLLEXUS - SMART- SOLUÇOES E SISTEMAS, LD",
    )
    product_company_website = fields.Char(
        "Website", readonly=True, default="https://compllexus.com"
    )
    product_company_tax_id = fields.Char(
        "Product Company Tax ID", readonly=True, default="5000856100"
    )
    agt_regime = fields.Selection(
        [("e", "Exclusão de IVA"), ("s", "Simplificado"), ("g", "Geral")], "Regime"
    )
    c_invoice_sequence_int = fields.Integer("ISI")

    vat = fields.Char(string="VAT")
    company_registry = fields.Char(string="company registry")
    zip = fields.Char(related="partner_id.zip", string="Zip Code")
    city = fields.Char(related="partner_id.city", string="City")
    state_id = fields.Many2one(
        comodel_name="res.country.state", related="partner_id.state_id", string="State"
    )
    country_id = fields.Many2one(
        comodel_name="res.country", related="partner_id.country_id", string="Country"
    )
    street = fields.Char(related="partner_id.street", readonly=False)

    def get_regime(self):
        if self.agt_regime == "e":
            return "Não Sujeição"
        if self.agt_regime == "s":
            return "Simplificado"
        if self.agt_regime == "g":
            return "Geral"

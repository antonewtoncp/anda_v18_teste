from odoo import fields, models, api


class AccountNotes(models.Model):
    _name = "account.note"
    _description = "Nota as Contas"

    name = fields.Char("Nome")
    code = fields.Char("Código")
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env["res.company"]._company_default_get(
            "account.note"
        ),
    )

    def name_get(self):
        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        self.read(["name", "code"])
        return [
            (
                template.id,
                "%s%s"
                % (template.code and "[%s] " % template.code or "", template.name),
            )
            for template in self
        ]


class AccountAccount(models.Model):
    _inherit = "account.account"

    account_note = fields.Many2one(comodel_name="account.note", string="Nota a Conta")


class AccountGroup(models.Model):
    _inherit = "account.group"

    account_note = fields.Many2one(comodel_name="account.note", string="Nota as Contas")

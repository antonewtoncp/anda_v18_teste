from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = "account.account"

    reason_code = fields.Char(string="Razão", tracking=True)
    integrator_code = fields.Char(string="Integradora", tracking=True)
    nature = fields.Selection(
        [
            ("C", "Classe"),
            ("R", "Razão"),
            ("I", "Integradora"),
            ("M", "Movimento"),
        ],
        string="Natureza",
        tracking=True,
    )

    @api.constrains("code")
    def _check_account_code(self):
        size = len(self.code)
        _code = self.code.replace(".", "")
        if size == 3:
            domain = [("code", "=", _code[:-1])]
            if self.env.user.has_group("base.group_multi_company"):
                company_id = (
                    self.env.company.id
                    if not self.env.company.parent_id
                    else self.env.company.parent_id.id
                )
                domain.append(("company_ids", "in", [company_id]))
            if not self.env["account.account"].search(domain):
                raise UserError(
                    _(
                        "Conta Invalida.\n"
                        "Não existe conta de razão para a conta %s, consultar o contabilista."
                        % _code
                    )
                )
        elif size >= 4:
            if _code.count("0") != 0:
                _code = _code[: _code.find("0")]
            domain = [("code", "=", _code[:-1])]
            if self.env.user.has_group("base.group_multi_company"):
                company_id = (
                    self.env.company.id
                    if not self.env.company.parent_id
                    else self.env.company.parent_id.id
                )
                domain.extend([("company_ids", "in", [company_id])])
            account = self.env["account.account"].search(domain)
            if not account and self.env.company.control_account_nature:
                raise UserError(
                    _(
                        "Crie a conta integradora %s\nÉ necessário criar a conta integradora primeiro"
                    )
                    % _code[:-1]
                )

    def check_nature(self, res_id):
        if not res_id or not res_id.code:
            return
        size = len(res_id.code)
        _code = res_id.code.replace(".", "")
        if _code:
            if size == 1:
                res_id.nature = "C"
            elif size == 2:
                res_id.nature = "R"
            elif size == 3:
                res_id.nature = "I"
                res_id.reason_code = res_id.get_reason_code(_code)
            elif size >= 4:
                if _code.count("0") != 0:
                    _code = _code[: _code.find("0")]
                domain = [("code", "=", _code[:-1])]
                if self.env.user.has_group("base.group_multi_company"):
                    company_id = (
                        res_id.company_ids.id
                        if not res_id.company_ids.parent_id
                        else res_id.company_ids.parent_id.id
                    )
                    domain.append(("company_ids", "in", [company_id]))
                account = self.env["account.account"].search(domain)
                if account:
                    account.nature = "I"
                    res_id.nature = "M"
                    res_id.reason_code = res_id.get_reason_code(_code)
                    res_id.integrator_code = _code[:-1]

    def write(self, vals):
        if vals.get("code"):
            vals["code"] = vals["code"].replace(" ", "")
            for res in self:
                self.check_nature(res)
        return super(AccountAccount, self).write(vals)

    @api.model
    def create(self, vals_list):
        result = super(AccountAccount, self).create(vals_list)
        self.check_nature(result)
        return result

    def get_reason_code(self, code):
        if self.env["account.account"].search([("code", "=", code[:2])]):
            return code[:2]
        return ""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _rec_name = "name"

    @api.onchange("is_storable", "categ_id")
    def _onchange_product_type(self):
        """Ajusta contas e comportamento com base no campo `is_storable`."""
        code_sale = "61"
        code_purchase = "21"

        if not self.is_storable:  # Produto não armazenável
            self.sale_ok = True
            code_sale = (
                "62"
                + str(self.categ_id.property_service_plan_sale or "")
                + str(self.categ_id.property_act_plan_sale or "")
            )
            code_purchase = "752191"
            account = self.env["account.account"].search(
                [("code", "=", code_sale)], limit=1
            )
            account_purchase = self.env["account.account"].search(
                [("code", "=", code_purchase)], limit=1
            )

            self.property_account_income_id = account or False
            self.property_account_expense_id = account_purchase or False

        else:  # Produto armazenável
            self.sale_ok = True
            code_sale += str(self.categ_id.property_plan_sale or "") + str(
                self.categ_id.property_act_plan_sale or ""
            )
            code_purchase += str(self.categ_id.property_plan_purchase or "") + str(
                self.categ_id.property_act_plan_purchase or ""
            )
            account = self.env["account.account"].search(
                [("code", "=", code_sale)], limit=1
            )
            account_purchase = self.env["account.account"].search(
                [("code", "=", code_purchase)], limit=1
            )

            self.property_account_income_id = account or False
            self.property_account_expense_id = account_purchase or False

    @api.onchange("is_storable")
    def _onchange_is_storable(self):
        if self.is_storable:
            self.categ_id = False  # Limpar a categoria para reavaliar o domínio.
            return {"domain": {"categ_id": [("type", "=", "product")]}}
        else:
            self.categ_id = False  # Limpar a categoria para reavaliar o domínio.
            return {"domain": {"categ_id": [("type", "=", "consu")]}}

    @api.constrains("name", "list_price", "standard_price")
    def check_sale_price(self):
        """Impede preços negativos em `list_price` e `standard_price`."""
        for res in self:
            if res.list_price < 0:
                res.list_price = 0
            if res.standard_price < 0:
                res.standard_price = 0

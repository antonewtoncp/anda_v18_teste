from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime


class ArticleResumeWizard(models.TransientModel):
    _name = "article.resume.wizard"
    _description = "Report for article extract"

    start_date = fields.Date(string="Start Date", default=fields.Date.today)
    end_date = fields.Date(string="End Date", default=fields.Date.today)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda l: l.env.user.company_id,
        string="Company",
    )
    product_id = fields.Many2one(
        string="Product", comodel_name="product.product", readonly=True
    )

    # Constraint for date validation
    @api.constrains("start_date", "end_date")
    def check_date(self):
        if self.start_date > self.end_date:
            raise ValidationError(
                _("Start date cannot be greater than end date. Please check dates.")
            )

    # Print report method
    def print(self):
        product = self.product_id
        if product:
            total_sales = (product.qty_available or 0) * (product.list_price or 0)
            total_purchase = (product.purchased_product_qty or 0) * (
                product.standard_price or 0
            )
            margin = total_sales - total_purchase

            # Calculando a quantidade vendida
            sale_lines = self.env["sale.order.line"].search(
                [
                    ("product_id", "=", product.id),
                    (
                        "state",
                        "in",
                        ["sale", "done"],
                    ),  # Considera vendas confirmadas e feitas
                ]
            )
            quantity_sold = sum(sale_lines.mapped("product_uom_qty"))

            # Passar os valores calculados para o contexto
            self = self.with_context(
                total_sales=total_sales,
                total_purchase=total_purchase,
                margin=margin,
                quantity_sold=quantity_sold,  # Quantidade já vendida
            )

        return self.env.ref("ht_stock_ao.action_article_resume_report").report_action(
            self
        )

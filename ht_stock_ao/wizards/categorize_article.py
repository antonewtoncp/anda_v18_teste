from odoo import models, fields


class CategorizeArticleWizard(models.TransientModel):
    _name = "wizard.categorize.article"

    category_id = fields.Many2one(
        string="Categoria",
        comodel_name="product.category",
    )

    product_ids = fields.Many2many(comodel_name="product.product", string="Artigos")

    def categorize_article(self):
        for product in self.product_ids:
            product.categ_id = self.category_id.id

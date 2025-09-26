from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SAFTProductProduct(models.Model):
    _inherit = "product.product"

    un_number = fields.Char(
        string="UNNumber", help="Preencher com o nª ONU para produtos perigosos"
    )
    customs_details = fields.Text(string="Customs Details")

    def write(self, values):
        if values.get("name") or values.get("description"):
            invoices = self.env["account.move"].search(
                [("state", "in", ["open", "paid"])]
            )
            if invoices:
                invoice_lines = invoices.mapped("invoice_line_ids")
                invoice_lines_p = invoice_lines.filtered(
                    lambda r: r.product_id.id == self.id
                )

                if invoice_lines_p:
                    if "name" in values:
                        values.pop("name")
                    if "description" in values:
                        values.pop("description")
                return super(SAFTProductProduct, self).write(values)
        else:
            return super(SAFTProductProduct, self).write(values)

    @staticmethod
    def check_product_type(product_type):
        if product_type in ["service", "monthly"]:
            return "S"
        return "P"

    def get_content_saf_t_ao(self, invoices):
        result = {"Product": []}
        # if we have some very bad invoices with no product in lines we use it default
        default_product = {
            "ProductType": "S",
            "ProductCode": "HS12D",
            "ProductGroup": "Todos",
            "ProductDescription": "Serviços",
            "ProductNumberCode": "HS12D",
            # 'CustomsDetails': product.customs_details or "",
        }
        all_products = self.with_context(active_test=False).search([])

        for product in all_products:
            if product.id not in invoices.mapped("invoice_line_ids").mapped("product_id").ids:
                continue

            product_val = {
                "ProductType": product.check_product_type(product.type),
                "ProductCode": product.id,
                "ProductGroup": product.categ_id.name,
                "ProductDescription": (
                    product.description_sale.strip()[:200]
                    if product.description_sale
                    else product.name.strip()[:200]
                ),
                "ProductNumberCode": product.barcode or product.id,
                # 'CustomsDetails': product.customs_details or "",
            }
            if product.un_number:
                product_val["UNNumber"] = product.un_number
            result["Product"].append(product_val)
        result["Product"].append(default_product)
        return result

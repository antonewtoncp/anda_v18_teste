from odoo import fields, models, api
import logging
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    amount_total_wth = fields.Monetary(
        string="Total com Retenção", readonly=True, compute="_compute_wth_values"
    )
    amount_wth_apply = fields.Monetary(
        string="Retenção Aplicada", readonly=True, compute="_compute_wth_values"
    )

    cost_center = fields.Many2one(
        comodel_name="account.cost.center", string="Centro de Custos"
    )
    has_cost_center = fields.Boolean(related="company_id.sale_cost_center")

    def _prepare_invoice(self):
        result = super(SaleOrder, self)._prepare_invoice()
        result["invoice_origin"] = (
            self.name + " - " + fields.Datetime.to_string(self.date_order)[:10]
        )
        result["cost_center"] = self.cost_center.id
        return result

    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        for picking in self.picking_ids:
            if self.cost_center:
                picking.cost_center = self.cost_center.id
        return result

    def get_tax_line_details(self):
        """return: data for all taxes"""
        tax_lines_data = []
        for line in self.order_line:
            for tax_line in line.tax_id:
                tax_lines_data.append(
                    {
                        "tax_exigibility": tax_line.tax_exigibility,
                        "tax_amount": line.price_subtotal * (tax_line.amount / 100),
                        "base_amount": line.price_subtotal,
                        "tax": tax_line,
                    }
                )
        return tax_lines_data

    def tax_of_invoice(self):
        taxes = []
        for line in self.order_line:
            for tax in line.tax_id:
                taxes.append(tax)
        return list(set(taxes))

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    @api.depends("order_line.tax_id")
    def _compute_wth_values(self):
        for record in self:
            wth_apply = 0
            for line in record.order_line:
                withholding_taxes = line.tax_id.filtered(
                    lambda tax: tax.tax_exigibility == "withholding"
                )

                for tax in withholding_taxes:
                    wth_apply += line.price_subtotal * (tax.amount_retention / 100)

            record.amount_wth_apply = wth_apply
            record.amount_total_wth = record.amount_total - wth_apply

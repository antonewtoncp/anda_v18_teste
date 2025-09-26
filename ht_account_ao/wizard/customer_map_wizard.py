from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time


class CustomerInvoice(models.TransientModel):
    _name = "customer.map.wizard"
    _description = "Customer  Map"

    start_date = fields.Date(
        string="Data de Início",
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)),
    )
    end_date = fields.Date(
        string="Data de Fim",
        default=lambda self: fields.Date.to_string(
            (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        ),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda l: l.env.user.company_id,
        string="Empresa",
    )

    @api.constrains("start_date", "end_date")
    def check_date(self):
        if self.start_date > self.end_date:
            raise ValidationError(
                _(
                    "Data Final não pode ser Menor que a data inicial\n"
                    " Por favor, Verifique as datas."
                )
            )

    def get_customer(self):
        customers = []
        customer = self.env["account.move"].search(
            [
                ("date", ">=", self.start_date),
                ("date", "<=", self.end_date),
                ("company_id", "=", self.company_id.id),
                ("state", "=", "posted"),
                ("move_type", "=", "out_invoice"),
            ],
            order="sequence_int asc",
        )

        for record in customer:
            data = {
                "name": record.partner_id.name,
                "ref": record.ref,
                "date": record.invoice_date,
                "type": "FT",
                "vat": record.partner_id.vat,
                "partner": record.partner_id,
                "reference": record.ref,
                "number": record.sequence_number,
                "order_number": record.name,
                "amount_total": record.amount_total,
                "amount_untaxed": record.amount_untaxed,
                "amount_tax": record.amount_tax,
                # new lines add
                "tributal_amount": record.name,
                "supported_iva": "Todos",
                "deductivel_iva": record.amount_wth_apply,
                "reduzed_iva_percent": record.amount_wth_apply,
                "reduzed_iva_amount": record.amount_tax,
                "tipologia": record.amount_tax,
                "model_camp": record.amount_tax,
            }
            customers.append(data)
        return customers

    def print(self):
        return self.env.ref("ht_account_ao.action_customer_map_report").report_action(
            self
        )

    def print_xlsx_report(self):
        return self.env.ref("ht_account_ao.action_report_customer_map").report_action(
            self
        )

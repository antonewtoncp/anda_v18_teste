import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from odoo.tools.translate import _
from odoo.exceptions import UserError
import calendar
from ..models import utils

from odoo import api, fields, models


class WizardSalary(models.TransientModel):
    _name = 'wizard.bank.template'
    _description = 'Print BANK Template'

    hr_payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip Batch',
                                        help='Select the Payslip Batch for wich you want do generate the Salary map Report')
    company_id = fields.Many2one(
        'res.company',
        string="Empresa",
        default=lambda self: self.env.company,
        required=True
    )

    payment_map_xls = fields.Binary("Ficheiro", readonly=True)
    payment_map_xls_filename = fields.Char("Nome do ficheiro")
    
    def generate_payment_partner_xls(self):
        payment_map_data = []
        payment = {
            "rows": [],
            "info": {
                "create_date": f"{self.hr_payslip_run_id.create_date.day}-{self.hr_payslip_run_id.create_date.month}-{self.hr_payslip_run_id.create_date.year}",
                "reference": self.hr_payslip_run_id.name
            }
        }
        payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', self.hr_payslip_run_id.id)])
        order_number = 0
        meses = {
            1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
            5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
            9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
        }

        for slip in payslips:
            order_number += 1
            res = {
                'nome': slip.employee_id.name,
                'batch': self.hr_payslip_run_id.name,
                'order': f"ORD {meses[self.create_date.month]}",
                'bank': 'LUANDA',
                'iban': slip.employee_id.bank_iban,
                'valor': slip.total_paid
            }
            payment_map_data.append(res)
        payment['rows'] = payment_map_data
        
        return payment


    def print_report(self):
        payment_map = self.generate_payment_partner_xls()

        xls_content = utils.generate_bank_sheet(payment_map, self.company_id)

        self.payment_map_xls = xls_content
        self.payment_map_xls_filename = f"{self.hr_payslip_run_id.name}_mapa_pagamento.xlsx"

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model=wizard.bank.template&id={self.id}&field=payment_map_xls&filename_field=payment_map_xls_filename&download=true",
            'target': 'new',
        }
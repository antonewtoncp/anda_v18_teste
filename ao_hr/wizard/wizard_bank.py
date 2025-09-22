import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from odoo.tools.translate import _
from odoo.exceptions import UserError
import calendar

from odoo import api, fields, models


class WizardSalary(models.TransientModel):
    _name = 'wizard.bank'
    _description = 'Print BANK Map'

    bank = fields.Many2one('res.bank', string='Bank', required='True', help='Select the bank for print the declaration')
    slip_filter_by = fields.Selection([('payslip_batch', 'Bayslip Batch'), ('payslip_date', 'Payslip Date')],
                                      'Filter By', required=True,
                                      help='Select the methond to capture the Payslips. You can choose Payslip Batch or by Date')
    hr_payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip Batch',
                                        help='Select the Payslip Batch for wich you want do generate the Salary map Report')
    start_date = fields.Date('Start Date', default=time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date',
                           default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    company_id = fields.Many2one("res.company", string="Company", required=True,
                                 default=lambda self: self.env.user.company_id.id)

    def _check_dates(self):
        for payslip in self:
            if payslip.start_date > payslip.end_date:
                return False
        return True

    _constraints = [(_check_dates, "'Start Date' must be less than 'End Date'.", ['Start Date', 'End Date'])]

    def get_lines(self):
        for payslip in self:
            if payslip.slip_filter_by == 'payslip_batch':
                return [id for id in payslip.hr_payslip_run_id.slip_ids if id.employee_id.bank_bank == self.bank.id]
            else:
                return [id for id in self.env['hr.payslip'].search([('date_from', '>=', self.start_date),
                                                                    ('date_to', '<=', self.end_date),
                                                                    ('employee_id.bank_bank', '=', self.bank.id)])]

    def get_date(self):
        meses = ['Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro',
                 'Novembro', 'Dezembro']
        return 'Luanda aos %d de %s de %d' % (datetime.now().day, meses[datetime.now().month - 1], datetime.now().year)

    def print_report(self):
        data = {'form': self.read(['slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date', 'bank'])[0]}
        return self.env.ref('ao_hr.action_report_bank').report_action(self, data=data)

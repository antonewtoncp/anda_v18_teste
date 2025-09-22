# import time
# from datetime import datetime
# from dateutil import relativedelta
# from odoo import api, fields, models, _
# from odoo.exceptions import ValidationError
#
#
# class WizardIRT(models.TransientModel):
#     _name = 'wizard.irt'
#     _description = 'Print IRT Map'
#     _rec_name = "company_id"
#
#     slip_filter_by = fields.Selection([
#         ('payslip_batch', 'Payslip Batch'),
#         ('payslip_date', 'Payslip Date'),
#         ('year', 'Fiscal Year')
#     ], 'Filter By', required=True,
#         help='Select the methond to capture the Payslips. You can choose Payslip Batch or by Date')
#     hr_payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip Batch',
#                                         help='Select the Payslip Batch for wich you want do generate the Salary map Report')
#     start_date = fields.Date('Start Date', default=time.strftime('%Y-%m-01'))
#     end_date = fields.Date('End Date',
#                            default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
#     company_id = fields.Many2one("res.company", string="Company", required=True,
#                                  default=lambda self: self.env.user.company_id.id)
#
#     fiscal_year = fields.Integer('Fiscal Year')
#     group = fields.Selection([('group_a', 'Grupo A'), ('group_bc', 'Grupo B - C')], string='Group', default='group_a')
#
#     @api.constrains('start_date', 'end_date')
#     def check_dates(self):
#         if self.start_date > self.end_date:
#             raise ValidationError('Start Date must be lower than End Date')
#
#     def print_report(self):
#         data = {
#             'form': self.read([
#                 'group', 'slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date', 'fiscal_year'
#             ])[0]
#         }
#         if self.group == 'group_a':
#             return self.env.ref('ao_hr.action_report_irt_group_a').report_action(self, data=data)
#         elif self.group == 'group_bc':
#             return self.env.ref('ao_hr.action_report_irt_group_bc').report_action(self, data=data)
#
#     def print_report(self):
#         return self.env.ref('ao_hr.action_report_irt').report_action(self, data={
#             'form': self.read(['slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date', 'fiscal_year'])[0]})

import time
from datetime import datetime
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WizardIRT(models.TransientModel):
    _name = 'wizard.irt'
    _description = 'Print IRT Map'
    _rec_name = "company_id"

    slip_filter_by = fields.Selection([
        ('payslip_batch', 'Payslip Batch'),
        ('payslip_date', 'Payslip Date'),
        ('year', 'Fiscal Year')
    ], 'Filter By', required=True,
        help='Select the methond to capture the Payslips. You can choose Payslip Batch or by Date')
    hr_payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip Batch',
                                        help='Select the Payslip Batch for wich you want do generate the Salary map Report')
    start_date = fields.Date('Start Date', default=time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date',
                           default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    company_id = fields.Many2one("res.company", string="Company", required=True,
                                 default=lambda self: self.env.user.company_id.id)

    fiscal_year = fields.Integer('Fiscal Year')
    group = fields.Selection([('group_a', 'Grupo A'), ('group_bc', 'Grupo B - C')], string='Group', default='group_a')

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be lower than End Date')

    def print_xlsx_report(self):

        if self.slip_filter_by == 'payslip_batch':
            search_paylip = self.env['hr.payslip'].search([('payslip_run_id', '=', self.hr_payslip_run_id.name)],
                                                          order='employee_name asc')

            dados = []
            count_reg = 0
            # verifica se o valor de um determinado campo é false.
            check_booleans = lambda x: x if x != False else ''
            round_number = lambda x: round(float(x), 2)
            for paylip in search_paylip:
                count_reg += 1

                dados.append({
                    'employ_number': count_reg,
                    'employ_fiscal_number': check_booleans(paylip.employee_id.fiscal_number),
                    'employ_name': paylip.employee_id.name,
                    'employ_social_security': check_booleans(paylip.employee_id.social_security),
                    'employ_province': check_booleans(paylip.employee_id.location_province.name),
                    'employ_county': check_booleans(paylip.employee_id.location_province.name),
                    'amount_base': round_number(paylip.amount_base_irt),
                    'descount_misses': paylip.misses,
                    'sub_alimentation': paylip.sub_ali,
                    'sub_transport': paylip.sub_trans,
                    'sub_family': paylip.abono_fam,
                    'expenses_refund': 0,
                    'others': paylip.total_sub_other,
                    'calculation_excess': '',
                    'sub_excess': '',
                    'fail_allowance': '',
                    'sub_home': '',
                    'compensation_termination': '',
                    'sub_holiday': round_number(paylip.sub_holiday),
                    'overtimes': round_number(paylip.overtimes),
                    'sub_atavio': '',
                    'sub_representation': '',
                    'sub_premier': '',
                    'sub_natal': '',
                    'others_subject': '',
                    'salary_iliquid': '',
                    'registry_manual': '',
                    'base_security_social': '',
                    'dont_subject_social': '',
                    'contribute_security_social': '',
                    'base_tribute_IRT': '',
                    'tax_exemption': '',
                    'apart_irt': '',
                })
                pass
            return self.env.ref('ao_hr.action_report_map_irt_xls').report_action(self, data={'data': dados})

    pass

    def print_report(self):
        data = {
            'form': self.read([
                'group', 'slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date', 'fiscal_year'
            ])[0]
        }
        if self.group == 'group_a':
            return self.env.ref('ao_hr.action_report_irt_group_a').report_action(self, data=data)
        elif self.group == 'group_bc':
            return self.env.ref('ao_hr.action_report_irt_group_bc').report_action(self, data=data)

# def print_report(self):
#     return self.env.ref('ao_hr.action_report_irt').report_action(self, data={
#         'form': self.read(['slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date', 'fiscal_year'])[0]})


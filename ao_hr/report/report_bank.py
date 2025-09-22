# -*- coding: utf-8 -*-

import time
from odoo import api, models, fields, _
from dateutil.parser import parse
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang


class ReportBank(models.AbstractModel):
    _name = 'report.ao_hr.report_bank'
    _description = "Bank Report"

    def _get_report_values(self, docids, data=None):
        docs = slip_obj = period_date_obj = None
        slip_filter_by = data['form']['slip_filter_by']

        if slip_filter_by == 'payslip_batch':
            slip_id = data['form']['hr_payslip_run_id'][0]
            docs = self.env['hr.payslip'].search([('payslip_run_id', '=', slip_id)], order='employee_name asc')
            slip_obj = docs.mapped("payslip_run_id")
            period_date = self.env['hr.payslip.run'].browse(slip_id).date_start
        else:
            start_date = data['form']['start_date']
            end_date = data['form']['end_date']
            slip_id = data['form']['hr_payslip_run_id'][0]
            period_date = parse(str(end_date))
            docs = self.env['hr.payslip'].search([('payslip_run_id', '=', slip_id)])
            slip_obj = docs.mapped("payslip_run_id")
            docs = self.env['hr.payslip'].search([('date_to', '>=', start_date), ('date_to', '<=', end_date)], order='employee_name asc')
        if not docs:
            raise ValidationError('There is no payslips that match this criteria')

        months = {
            1: _('January'),
            2: _('February'),
            3: _('March'),
            4: _('April'),
            5: _('May'),
            6: _('June'),
            7: _('July'),
            8: _('August'),
            9: _('September'),
            10: _('October'),
            11: _('November'),
            12: _('December'),
        }

        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'time': time,
            'data': data['form'],
            'formatLang': formatLang,
            'env': self.env,
            'slip_run': slip_obj,
            'period': '%s de %d' % (months[period_date.month], period_date.year)
        }

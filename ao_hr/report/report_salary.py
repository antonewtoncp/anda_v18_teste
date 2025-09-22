# -*- coding: utf-8 -*-

import time
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang
from . import report_common


class ReportSalary(models.AbstractModel):
    _name = 'report.ao_hr.report_salary'
    _description = "Salary Report Sheet"

    @api.model
    def _get_report_values(self, docids, data=None):
        slip_obj = docs = period_date_obj = None
        slip_filter_by = data['form']['slip_filter_by']

        if slip_filter_by == 'payslip_batch':
            slip_id = data['form']['hr_payslip_run_id'][0]
            slip_obj = self.env['hr.payslip.run'].search([('id', '=', slip_id)])
            docs = self.env['hr.payslip'].search([('payslip_run_id', '=', slip_id)], order='employee_name asc')
            period_date = self.env['hr.payslip.run'].browse(slip_id).date_end
        else:
            start_date = data['form']['start_date']
            end_date = data['form']['end_date']
            slip_id = data['form']['hr_payslip_run_id'][0]
            slip_obj = self.env['hr.payslip.run'].search([('id', '=', slip_id)])
            period_date = start_date
            docs = self.env['hr.payslip'].search([('date_to', '>=', start_date), ('date_to', '<=', end_date)], order='employee_name asc')
        if not docs:
            raise ValidationError('There is no payslips that match this criteria')
        
        rules_remuneracao = set()
        rules_desconto = set()
        for slip in docs:
            for line in slip.line_ids:
                # Ignora GROSS e NET
                if line.code in ["GROSS", "NET"]:
                    continue
                # Ignora IRT e DED
                if line.category_id.code in ["IRT", "INSS"]:
                    continue
                # Ignora linhas que não aparecem no recibo
                if not line.appears_on_payslip:
                    continue
                # Ignora linhas que não aparecem no contracheque
                if not line.appears_on_payslip:
                    continue
                if line.total > 0:
                    rules_remuneracao.add((line.code, line.name))
                elif line.total < 0:
                    rules_desconto.add((line.code, line.name))
        
        # Monta dicionário auxiliar de nomes formatados
        nomes_formatados = {}
        for slip in docs:
            if slip.employee_id.name:
                partes = slip.employee_id.name.strip().split()
                if len(partes) > 1:
                    nomes_formatados[slip.id] = f"{partes[0]} {partes[-1]}"
                else:
                    nomes_formatados[slip.id] = slip.employee_id.name
            else:
                nomes_formatados[slip.id] = ""
        
        

        # Define a ordem personalizada
        ordem_prioridade_remuneracao = {
            "Vencimento": 0,
            "Subsídio de Alimentação": 1,
            "Subsídio de Transporte": 2,
            "Abono de Família": 3,
        }
        ordem_prioridade_desconto = {
            "Materia coletável Segurança Social": 0,
            "IRT": 1,
            "Falta Injustificada": 2,
            "Falta Justificada Não Remunerada": 3,
        }
        # Ordena por nome para manter consistência visual
        rules_remuneracao = sorted(
            list(rules_remuneracao),
            key=lambda x: (ordem_prioridade_remuneracao.get(x[1], 99), x[1]),
        )
        rules_desconto = sorted(
            list(rules_desconto),
            key=lambda x: (ordem_prioridade_desconto.get(x[1], 99), x[1]),
        )

        
        return {
            "doc_ids": docs.ids,
            "doc_model": "hr.payslip",
            "docs": docs,
            "time": time,
            "slip_run": slip_obj,
            "formatLang": formatLang,
            "filter_by": slip_filter_by,
            "env": self.env,
            "period": "%s de %d"
            % (report_common.get_month_text(period_date.month), period_date.year),
            "rem_tam": len(rules_remuneracao) + 1,
            "des_tam": len(rules_desconto) + 2,
            "rules_remuneracao": rules_remuneracao,
            "rules_desconto": rules_desconto,
            "nomes_formatados": nomes_formatados,
        }

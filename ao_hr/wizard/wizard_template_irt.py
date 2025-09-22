import time
from datetime import datetime, date
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import xlsxwriter
from io import BytesIO
import base64
from typing import Optional
from collections import defaultdict
from pprint import pprint

class WizardTemplateIRT(models.TransientModel):
    _name = 'wizard.template.irt'
    _description = 'Impressão do Mapa Salarial (IRT)'

    slip_filter_by = fields.Selection(
        [
            ('payslip_batch', 'Lote de folhas de pagamento'),
            ('payslip_date', 'Intervalo de datas'),
        ],
        string='Filtrar por',
        help='Selecione como deseja filtrar os dados para o relatório do Mapa Salarial.'
    )
    exercise_year = fields.Integer(name="Ano")
    date_from = fields.Date(string="Data inicial")
    date_to = fields.Date(string="Data final")
    group = fields.Selection([('year_exercise', 'Ano em exercício'), ('batch_or_date', 'Lote ou intervalo de data')], string='Por lote / ano', default='year_exercise')
    group_by = fields.Selection([('group_a', 'Grupo A'), ('group_bc', 'Grupo B - C')], string='Group', default='group_a')

    hr_payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Lote de folhas de pagamento',
        help='Selecione o lote de folhas de pagamento para o qual deseja gerar o relatório do Mapa Salarial.'
    )
    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        if self.date_from > self.date_to:
            raise ValidationError('Start Date must be lower than End Date')


    def calculate_not_absent_subs(
        self,
        basic_wage: float,
        sub_ali: Optional[float],
        sub_trans: Optional[float],
        sub_fam: Optional[float],
    ) -> float:
        """
        Calcula o valor total dos subsídios que devem ser abatidos em caso de ausência.

        - Inclui subsídio de férias, formação, produção, assistência e outros.
        - Inclui também subsídio de alimentação e transporte se <= 30.000.
        - Inclui subsídio familiar se for superior a 5% do salário base.
        """

      
        amount = 0.0
        if sub_ali is not None and sub_ali > 30000:
            amount += sub_ali - 30000

        if sub_trans is not None and sub_trans > 30000:
            amount += sub_trans - 30000

        if sub_fam is not None and sub_fam > 0.05 * basic_wage:
            amount += sub_fam - 0.05 * basic_wage

        return amount
    
    def _sum_remunerations(self, remunerations_list):
        if isinstance(remunerations_list, list) and all(isinstance(num, (int, float)) for num in remunerations_list):
            total = sum(remunerations_list)
            return total
        else:
            raise ValueError("O parâmetro deve ser uma lista de números.")
    
    def _sum_remunerations_irt(
            self, 
            basic_wage,
            sub_ali,
            sub_trans,
            sub_fam
        ):
        amount = basic_wage
        if (sub_ali > 30000):
            amount += sub_ali - 30000
        if (sub_trans > 30000):
            amount += sub_trans - 30000
        if (sub_fam > 0.05 * basic_wage):
            amount += sub_fam - 0.05 * basic_wage            
        return amount
    
    def exemption_irt(self, basic_wage, sub_ali, sub_trans, sub_fam):
        amount = 0
        if (sub_ali <= 30000):
            amount += sub_ali
        if (sub_trans <= 30000):
            amount += sub_trans
        if (sub_fam < 0.05 * basic_wage):
            amount += sub_fam            
        return amount
    
    def calcular_irt(self, wage):
        # Desconto de Segurança Social (3%)
        

        # Tabela progressiva (de, até, taxa, parcela fixa)
        escalas = [
            (0, 70000, 0.00, 0),
            (70000, 100000, 0.10, 3000),
            (100000, 150000, 0.13, 6000),
            (150000, 200000, 0.16, 12500),
            (200000, 300000, 0.18, 31250),
            (300000, 500000, 0.19, 49250),
            (500000, 1000000, 0.20, 87250),
            (1000000, 1500000, 0.21, 187250),
            (1500000, 2000000, 0.22, 292000),
            (2000000, 2500000, 0.23, 402250),
            (2500000, 5000000, 0.24, 517250),
            (5000000, 10000000, 0.245, 1117250),
            (10000000, float('inf'), 0.25, 2342250),
        ]

        irt = 0

        for de, ate, taxa, parcela_fixa in escalas:
            if wage > de and wage <= ate:
                excesso = wage - de + 1
                irt = (excesso * taxa) + parcela_fixa
                irt = max(0, irt)  # IRT nunca pode ser negativo
                break

        return irt
        

    def excel_template_one(self):
        output = BytesIO()

        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Mapa de IRT')
        # Definição de larguras das colunas
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 35)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 10)
        worksheet.set_column('E:E', 10)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 20)
        worksheet.set_column('H:H', 20)
        worksheet.set_column('I:I', 20)
        worksheet.set_column('J:J', 20)
        worksheet.set_column('K:K', 20)
        worksheet.set_column('L:L', 20)
        worksheet.set_column('M:M', 20)
        worksheet.set_column('N:N', 25)
        worksheet.set_column('O:O', 25)
        
        # Definição de cabeçalhos
        worksheet.write(0, 0, 'NIF')
        worksheet.write(0, 1, 'Nome')
        worksheet.write(0, 2, 'Nº Segurança Social')
        worksheet.write(0, 3, 'Província')
        worksheet.write(0, 4, 'Município')
        worksheet.write(0, 5, 'Salário Base')
        worksheet.write(0, 6, 'Subsídios Não Sujeitos a IRT')
        worksheet.write(0, 7, 'Subsídios Sujeitos a IRT')
        worksheet.write(0, 8, 'Salário Ilíquido')
        worksheet.write(0, 9, 'Base Tributável Segurança Social')
        worksheet.write(0, 10, 'Não Sujeito a Segurança Social')
        worksheet.write(0, 11, 'Contribuição de Segurança Social')
        worksheet.write(0, 12, 'Base Tributável IRT')
        worksheet.write(0, 13, 'Isento IRT')
        worksheet.write(0, 14, 'IRT Apurado')
        
        docs = []
        if (self.slip_filter_by == 'payslip_batch'):
            slip_id = self.hr_payslip_run_id.id
            docs = self.env['hr.payslip'].search([('payslip_run_id', '=', slip_id)], order='employee_name asc')
        elif (self.slip_filter_by == 'payslip_date'):
            docs = self.env['hr.payslip'].search([
                ('date_from', '>=', self.date_from),
                ('date_to', '<=', self.date_to)
            ])
        row = 1
        
        if self.group_by == 'group_a':
            docs = docs.filtered(lambda r: r.contract_id.struct_id.code == 'BASE')
        elif self.group_by == 'group_bc':
            docs = docs.filtered(lambda r: r.contract_id.struct_id.code == 'CLASS_B')
            
        for payslip in docs:
            # print('/' * 90)
            # pprint(payslip.contract_id.struct_id.code)
            # print('/' * 90)
            total = self._sum_remunerations([payslip.basic_wage, payslip.sub_ali, payslip.sub_trans, payslip.sub_fam])
            irt_not_absent = self.calculate_not_absent_subs(payslip.basic_wage, payslip.sub_ali, payslip.sub_trans, payslip.sub_fam)
            social_security_base = self._sum_remunerations([payslip.basic_wage, payslip.sub_ali, payslip.sub_trans])
            not_social_security_base = self._sum_remunerations([payslip.sub_fam])
            social_security_contribution = social_security_base * 0.03
            irt_base = self._sum_remunerations_irt(payslip.basic_wage,payslip.sub_ali, payslip.sub_trans, payslip.sub_fam) - social_security_contribution
            exemption_irt = self.exemption_irt(payslip.basic_wage,payslip.sub_ali, payslip.sub_trans, payslip.sub_fam)
            irt = self.calcular_irt(irt_base)
            worksheet.write(row, 0, self._normalize_text(payslip.employee_id.fiscal_number))
            worksheet.write(row, 1, payslip.employee_id.name)
            worksheet.write(row, 2, self._normalize_text(payslip.employee_id.social_security))
            worksheet.write(row, 3, self._normalize_text(payslip.employee_id.location_province.name))
            worksheet.write(row, 5, payslip.basic_wage)
            worksheet.write(row, 6, exemption_irt)
            worksheet.write(row, 7, irt_not_absent)
            worksheet.write(row, 8, total)
            worksheet.write(row, 9, social_security_base)
            worksheet.write(row, 10, not_social_security_base)
            worksheet.write(row, 11, social_security_contribution)
            worksheet.write(row, 12, irt_base)
            worksheet.write(row, 13, 'Não' if irt else 'Sim')
            worksheet.write(row, 14, irt)
            row += 1
            
        workbook.close()

        excel_data = output.getvalue()
        
        attachment = self.env['ir.attachment'].create({
            'name': f'Payslips{self.date_from}-{self.date_to}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Retornar uma ação que permite o download do arquivo gerado
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
        
            
    def excel_template_two(self):
        output = BytesIO()

        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Payslips')
        worksheet.set_column('A:A', 20) # Definição de larguras das colunas
        worksheet.set_column('B:B', 40)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 30)
        worksheet.set_column('E:E', 30)
        worksheet.set_column('F:F', 45)
        
      
        # Cabeçalhos
        worksheet.write(0, 0, 'NIF')
        worksheet.write(0, 1, 'Nome')
        worksheet.write(0, 2, 'Nº Segurança Social')
        worksheet.write(0, 3, 'Província')
        worksheet.write(0, 4, 'Valor Global dos Rendimentos Pagos')
        worksheet.write(0, 5, 'Montante Total de Imposto Pago no Exercício Anterior')

        date_start = date(self.exercise_year, 1, 1)
        date_end = date(self.exercise_year, 12, 31)

        docs = self.env['hr.payslip'].search([
            ('date_from', '>=', date_start),
            ('date_from', '<=', date_end)
        ], order='employee_name asc')
        
        row = 1
        groups = defaultdict(list)
        if self.group_by == 'group_a':
            docs = docs.filtered(lambda r: r.contract_id.struct_id.code == 'BASE')
        elif self.group_by == 'group_bc':
            docs = docs.filtered(lambda r: r.contract_id.struct_id.code == 'CLASS_B')
        for item in docs:
            key = item["employee_id"]["id"]
            groups[key].append( 
                {
                    "id": item.id,
                    "employee_id": item.employee_id.id,
                    "name": item.employee_id.name,
                    "basic_wage": item.basic_wage,
                    "sub_ali": item.sub_ali,
                    "sub_trans": item.sub_trans,
                    "sub_fam": item.sub_fam,
                    "fiscal_number": item.employee_id.fiscal_number,
                    "social_security": item.employee_id.social_security,
                    "location_province": item.employee_id.location_province.name,
                    # "salario": item.amount, 
                }
            )
            
        results = []
        for employee_id, registros in groups.items():
            total, irt = self._sum_amounts(registros)
            results.append({
                "employee_id": employee_id,
                "name": registros[0]["name"],
                "province": registros[0]["location_province"],
                "fiscal_number": registros[0]["fiscal_number"],
                "social_security": registros[0]["social_security"],
                "total": total,
                "irt": irt,
            })
            
        for payslip in results:
            worksheet.write(row, 0, self._normalize_text(payslip["fiscal_number"]))
            worksheet.write(row, 1, payslip["name"])
            worksheet.write(row, 2, self._normalize_text(payslip["social_security"]))
            worksheet.write(row, 3, self._normalize_text(payslip["province"]))
            worksheet.write(row, 4, payslip["total"])
            worksheet.write(row, 5, payslip["irt"])
            row += 1
        

        workbook.close()

        excel_data = output.getvalue()

        attachment = self.env['ir.attachment'].create({
            'name': f'Mapa-IRT{datetime.now()}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Retornar uma ação que permite o download do arquivo gerado
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
        
    def _normalize_text(self, value):
        return value if value != False else ''
    
    def export_payslip_to_excel(self):
        if (self.group == 'batch_or_date'):
            return self.excel_template_one()
        elif(self.group == 'year_exercise'):
            print('/' * 90)
            return self.excel_template_two()
        # Criação do arquivo Excel em memória
        
    def _sum_amounts(self, employees):
        total = 0
        irt = 0
        if isinstance(employees, list):
            for employee in employees:           
                social_security_base = self._sum_remunerations([employee["basic_wage"], employee["sub_ali"], employee["sub_trans"]])
                social_security_contribution = social_security_base * 0.03
                irt_base = self._sum_remunerations_irt(employee["basic_wage"],employee["sub_ali"], employee["sub_trans"], employee["sub_fam"]) - social_security_contribution
                irt += self.calcular_irt(irt_base)
                total += self._sum_remunerations([employee["basic_wage"], employee["sub_ali"], employee["sub_trans"], employee["sub_fam"]])

        return total, irt
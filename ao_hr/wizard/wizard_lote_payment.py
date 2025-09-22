import time
from datetime import datetime
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.parser import parse
from odoo.tools.misc import formatLang
from ..report import report_common


class WizardPayment(models.TransientModel):
    _name = 'wizard.payment'
    _description = 'Print Salary Map'
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
    type = fields.Selection([('ps2', 'PS2'), ('psx', 'PSX')], string='Tipo', default='ps2')
    operation_type = fields.Selection([('salary','Ordenados'),('water','água'),('gas','Gás')]
                                      ,string='Tipo de Operação',default='salary')

    account_debit_nib = fields.Char('NIB da Conta a Debitar', size=20, tracking=True)
    processing_date = fields.Date(' Data Processamento', default=fields.Date.today)
    owner_reference = fields.Char( string='Referência do Ordenante ')

    ##########################
    # #campos para o Tipo PSX#
    ##########################

    category = fields.Selection([('cash', 'Cash : Pagamentos '),
                                 ('govt', 'GOVT : Pagamentos ao estado/governo'),
                                 ('other', 'OTRF: Outros'),('pens', 'PENS :Pagamentos de pensões/benefícios'),
                                 ('sala', 'SALA : Pagamentos de salário/folha de pagamento'),
                                 ('ssbe', 'SSBE : Pagamentos de Segurança Social'),
                                 ('supp', 'SUPP: Fornecedores/Vendedores '),
                                 ('trad', 'TRAD : Bens'),
                                 ], string='Categoria', default='cash')

    urgency = fields.Selection([('urg', 'URG : Pagamento Urgente – Pagamentos '
                                'prioritários, sujeitos a prazos limite e sobretaxas'),
                               ('nor', 'NOR : Pagamento Normal – Valor Padrão'),
                               ], string='Urgência', default='urg')

    reason = fields.Selection([ ('almy', 'ALMY : Pagamentos de pensão alimentícia'),
                                ('bech', 'BECH : Prestações familiares (Abono de Família)'),
                                ('bene', 'BENE: Unemployment Benefits'),
                                ('cash', 'CASH: Benefícios de desemprego'),
                                ('cmdt', 'CMDT : Mercadorias'),
                                ('gods', 'GDDS: Compra/Venda Geral de Mercadorias'),
                                ('govt', 'GOVT : Reembolsos governamentais'),
                                ('hspc', 'HSPC : Cuidados Hospitalares'),
                                ('mdcs', 'MDCS	Cuidados Médicos'),
                                ('msvc', 'MSVC : Vários tipos de serviços'),
                                ('othr', 'OTHR : Outros'),
                                ('pens', 'PENS : Pensões/Benefícios'),
                                ('sala', 'SALA : Salários'),
                                ('rinp', 'RINP: Devolução do pagamento da fatura')
                                ,('scve', 'SCVE	Compra/Venda de serviço'),
                                ('supp', 'SUPP :Fornecedores')
                                   ,('ssbe', 'SSBE: Benefícios da Segurança Social'),
                                ('trad', 'TRAD : Bens'),
                                ('util', 'UTIL : Utilitárias')], string='Motivo', default='almy')

    transfer_type = fields.Selection([('stc', 'Pagamento STC Kwanza'),
                                      ('ptr', 'Pagamento SPTR em Kwanza em Tempo Real')],
                                     string='Tipo de Transferência', default='stc')

    details = fields.Selection([('ben', 'BEN : Beneficiário – Todos os encargos a serem pagos pelo Beneficiário'),
                                ('our', 'OUR : Nossa – Todas as despesas serão pagas pelo Cliente solicitante'),
                                ('sha', 'SHA : Compartilhado – Encargos do remetente para o cliente solicitante e encargos de recebimento pelo cliente beneficiário')],
                               string='Detalhes', default='ben')

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be lower than End Date')

    def print_xlsx_report(self):
        if self.slip_filter_by == 'payslip_batch':
            search_paylip = self.env['hr.payslip'].search([
                ('payslip_run_id', '=', self.hr_payslip_run_id.name)],
                  order='employee_name asc')

            dados = []
            count_reg = 0
            check_booleans = lambda x: x if x != False else ''
            round_number = lambda x: round(float(x), 2)

            for paylip in search_paylip:
                count_reg += 1

                if self.type == 'ps2':
                    #######################################
                    # Campos específicos para o tipo 'ps2'#
                    #######################################

                    dados.append({
                        'iban': check_booleans(paylip.employee_id.bank_iban),
                        'montante': round_number(paylip.remuneration),
                        'nome': paylip.employee_id.name,
                        'referencia': count_reg,
                        'Email': check_booleans(paylip.employee_id.work_email),
                    })
                else:
                    dados.append({
                        'nib': check_booleans(paylip.employee_id.fiscal_number),
                        'montante': round_number(paylip.remuneration),
                        'tipo_de_tranferencia': dict(self._fields['transfer_type'].selection).get(self.transfer_type),
                        'nome': paylip.employee_id.name,
                        'morada': check_booleans(paylip.employee_id.address_home_id.name),
                        'bic': 0,
                        'iban': check_booleans(paylip.employee_id.bank_iban),
                        'motivo': dict(self._fields['reason'].selection).get(self.reason),
                        'categoria': dict(self._fields['urgency'].selection).get(self.urgency),
                        'detalhes': dict(self._fields['category'].selection).get(self.category),
                        'urgencia': dict(self._fields['details'].selection).get(self.details),

                    })
            ###################################################
            # Coleta os dados de início para a folha "Início "#
            ###################################################
            dados_inicio = {
                'operation_type': dict(self._fields['operation_type'].selection).get(self.operation_type),
                'account_debit_nib': self.account_debit_nib,
                'processing_date': self.processing_date.strftime('%Y-%m-%d'),
                'owner_reference': self.owner_reference,
                    }

            return self.env.ref('ao_hr.action_payment_lote_xls').report_action(self, data={'data': dados,
                                                                                           'dados_inicio': dados_inicio})



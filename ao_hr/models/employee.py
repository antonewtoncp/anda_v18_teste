from odoo import fields, models, api, _
from odoo.exceptions import ValidationError,UserError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
import base64

import re


class Employee(models.Model):
    _inherit = 'hr.employee'

    employee_number = fields.Char('Employee Number', tracking=True)
    # private_email = fields.Char(related='address_home_id.email', string="Email Privado", groups="hr.group_hr_user",
    #                             tracking=True)
    # phone = fields.Char(related='address_home_id.phone', related_sudo=False, readonly=False, string="Telefone Privado",
    #                     groups="hr.group_hr_user", tracking=True)
    notes = fields.Text('Notes', groups="hr.group_hr_user", tracking=True)
    color = fields.Integer('Índice de cores', default=0, groups="hr.group_hr_user", tracking=True)
    barcode = fields.Char(string="ID do crachá", help="ID usado para identificação do funcionário.",
                          groups="hr.group_hr_user",
                          copy=False, tracking=True)
    pin = fields.Char(string="PIN", groups="hr.group_hr_user", copy=False,
                      help="PIN usado para Check In/Out no Modo Quiosque (se habilitado na Configuração).",
                      tracking=True)
    bi_emission = fields.Date("Data de Emissão do BI")
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user", tracking=True, size=16)
    social_security = fields.Char('Número de segurança', size=10, tracking=True)
    fiscal_number = fields.Char('Número fiscal', size=14, tracking=True)
    registration_number = fields.Char('Número de registro do funcionário', groups="hr.group_hr_user", copy=False,
                                      tracking=True)

    payment_method = fields.Selection([('bank', 'Bank Transfer'), ('cash', 'Cash'), ('check', 'Check')],
                                      'Forma de pagamento', default='bank', tracking=True)
    admission_date = fields.Date('Data de início', tracking=True)
    last_work_date = fields.Date('Data final', tracking=True)
    age = fields.Integer('Idade', compute='_compute_age', store=True, tracking=True)
    bank_bank = fields.Many2one('res.bank', string='Banco', tracking=True)
    bank_account = fields.Char('Conta Bancaria', size=40, tracking=True)
    bank_iban = fields.Char('IBAN', size=25, tracking=True, default="AO06")
    is_foreign = fields.Boolean('É Estrangeiro?', help='If this employee is foreign, please check this box',
                                tracking=True)
    # company_assets = fields.Many2many(comodel_name='hr.contract.company.assets', string='Company Assets')
    emergence_contact = fields.Many2one(comodel_name='res.partner', string='Contato de Emergências')
    langs = fields.Many2many(comodel_name='res.lang', string='língua', tracking=True)
    father = fields.Many2one(comodel_name='hr.father', string='Pai', tracking=True)
    mother = fields.Many2one(comodel_name='hr.mother', string='Mãe', tracking=True)
    job_id = fields.Many2one(comodel_name='hr.job', string='Cargo', tracking=True)
    establishment = fields.Many2one(comodel_name='hr.establishment', string='Local de trabalho', tracking=True)
    country_id = fields.Many2one('res.country', 'Nationality (Country)',
                                 groups="hr.group_hr_user", default=lambda l: l._default_country(), tracking=True)
    qualification = fields.Text(string='Qualificação', tracking=True)
    certificate = fields.Selection(selection_add=[
        ('primary_school', 'Primary school'),
        ('high_school', 'High school'),
        ('pre_university', 'Pre University'),
        ('university_attendance', 'University Attendance'),
        ('licensed', 'Licensed'),
        ('postgraduate', 'Postgraduate'),
        ('postgraduate_professional_training', 'Postgraduate Professional Training'),
        ('phd', 'PHD')
    ], default='other', groups="hr.group_hr_user", tracking=True)
    vehicle = fields.Char(string='Company Vehicle', groups="hr.group_hr_user", tracking=True)
    contract_id = fields.Many2one('hr.contract', string='Current Contract',
                                  groups="hr.group_hr_user", domain="[('company_id', '=', company_id)]",
                                  help='Current contract of the employee', tracking=True)
    calendar_mismatch = fields.Boolean(related='contract_id.calendar_mismatch', tracking=True)
    exempt_irt = fields.Boolean(string="IRT", default=1, tracking=True)
    has_bi = fields.Boolean("BI ?", tracking=True)
    exempt_ss = fields.Boolean(string="SS", default=1, tracking=True)
    has_taxpayer_card = fields.Boolean("Cartão de contribuinte?", tracking=True)
    has_medical_certificate = fields.Boolean("Certificado médico ?", tracking=True)
    has_account_bank = fields.Boolean("Conta bancária ?", tracking=True)
    has_household = fields.Boolean("Doméstico(a) ?", tracking=True)
    has_driving_license = fields.Boolean("Carteira de motorista?", tracking=True)
    has_criminal_record = fields.Boolean("Registro criminal ?", tracking=True)
    has_certificates = fields.Boolean("Certificate ?", tracking=True)
    blacklist = fields.Boolean("Lista negra", tracking=True)
    sign_signature = fields.Binary(string="Assinatura digital", groups="base.group_system")
    functions_descriptions = fields.Text('Descrições das Funções')
    location_province = fields.Many2one('res.country.state', string='Provincia')
    County_address = fields.Many2one('res.country.state.county', string='Municipio')
    structure_type_id = fields.Many2one(comodel_name='hr.payroll.structure.type', string="Salary Structure Type")
    is_governing_body = fields.Boolean(string="Governing Body")
    end_date = fields.Datetime(string='End Date', default=datetime.now())
    cp_employee_type = fields.Selection([
        ('employee', 'Employee'),
        ('student', 'Student'),
        ('trainee', 'Trainee'),
        ('contractor', 'Contractor'),
        ('freelance', 'Freelancer'),
        ('o', 'Governing Body'),
    ], string='Employee Type', default='employee', required=True,
        help="The employee type. Although the primary purpose may seem to categorize employees, this field has also an impact in the Contract History. Only Employee type is supposed to be under contract and will have a Contract History.")

    @api.onchange('is_foreign')
    def _onchange_is_foreign(self):
        if self.is_foreign:
            self.bank_iban = False
            self.bi_emission = False
            self.location_province = False

    @api.constrains('work_phone', 'mobile_phone', 'work_email', 'name')
    def _check_phone_and_email(self):
        angola_phone_pattern = re.compile(r'^\d{9}$')
        email_pattern = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
        name_pattern = re.compile(r'^[A-Za-zÀ-ÖØ-öø-ÿ\s.,]*$')

        for record in self:
            if record.name and not name_pattern.match(record.name):
                raise ValidationError(
                    "O nome do trabalhador deve conter apenas caracteres alfabéticos, acentos, espaços, pontos e virgulas.")
            if record.work_phone and not angola_phone_pattern.match(record.work_phone):
                raise ValidationError(
                    "O número de telefone de trabalho de Angola deve conter exatamente 9 dígitos e apenas números.")
            if record.mobile_phone and not angola_phone_pattern.match(record.mobile_phone):
                raise ValidationError(
                    "O número do  Telémovel do Emprego de Angola deve conter exatamente 9 dígitos e apenas números.")
            if record.work_email and not email_pattern.match(record.work_email):
                raise ValidationError("O e-mail de trabalho deve ser um endereço de e-mail válido.")

    @api.onchange('is_governing_body')
    def onchange_is_governing_body(self):
        if self.is_governing_body:
            self.cp_employee_type = 'o'
        else:
            self.cp_employee_type = 'employee'

    @api.constrains('birthday')
    def _check_birth_date(self):
        for res in self:
            if res.birthday >= fields.Date.today():
                raise ValidationError(_(
                    "A data de nascimento não pode ser maior que a data atual!"))
            if res.birthday:
                res.age = fields.Date.today().year - res.birthday.year
                if res.age <=17:
                    raise ValidationError(_(
                        "Não é admitido funcionários menores de 18 anos\n"
                    ))

    @api.depends('birthday')
    def _compute_age(self):
        for res in self:
            if res.birthday:
                res.age = fields.Date.today().year - res.birthday.year

    def _default_country(self):
        return self.env.ref('base.ao').id

    @api.model
    def create(self, vals):
        result = super(Employee, self).create(vals)
        if result.father:
            result.father.child_ids |= result
        if result.mother:
            result.mother.child_ids |= result
        result.employee_number = self.env['ir.sequence'].next_by_code('hr.employee') or _('New')
        return result

    def get_all_employee_contract(self):
        contract_ids = self.env['hr.contract'].search([('employee_id', '=', self.id)])
        if contract_ids:
            return contract_ids

    # def _get_contract(self):
    #     contract = self.env['hr.contract'].search([('employee_id', '=', self.id)]).id
    #     return contract

    def get_all_employee_list(self):
        return self.env['hr.employee'].search([])

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "O nome desse Funcionário já existe na lista !"),
    ]

    @api.constrains('bank_iban')
    def _check_bank_iban(self):
        for record in self:
            iban = record.bank_iban
            if iban:
                if not (len(iban) == 25 and iban.startswith('AO06')) and not (
                        len(iban) == 21 and re.match(r'^\d{21}$', iban)):
                    raise ValidationError(
                        "O IBAN deve começar com AO06 seguido de 21 dígitos, ou consistir de exatamente 21 dígitos.")


class HrEstablishment(models.Model):
    _name = 'hr.establishment'

    name = fields.Char(string="Work Location")


class ContractActiveCompany(models.Model):
    _name = 'hr.contract.company.assets'
    _description = 'Company Assets'

    name = fields.Char(string='Name')
    purchase_date = fields.Date('Purchase Date')
    ref = fields.Char(string='Reference')
    cost_price = fields.Float(string='Cost')
    

class ContractProposall(models.Model):
    _inherit = 'hr.applicant'
    
    nationality = fields.Selection([('nacional','Nacional'),('estrangeira','Estrangeira')],string='Nacionalidade', required=True)
    experience_year_function = fields.Integer(string='Anos de Experiência', required=True)
    
    # funtion = fields.Selection([('desenvolvidorodoo','Desenvolvedor Odoo'), 
    #                             ('Assitentecontabilidade','Assitente de Contabilidade'),
    #                             ('analistadesistema','Analsita de Sistemas')],string='Função', required=True)
    job_id = fields.Many2one(comodel_name='hr.job', string='Função', tracking=True)
    category = fields.Selection([('junior','Junior'),('senior', 'Senior'), ('pleno', 'Pleno')],string='Categoria', required=True)
    report = fields.Selection([('chefedepartamento','Chefe departamento'),
                               ('directorexecutivo', 'Director Executivo')],string='Reporte', required=True)
    start_date = fields.Date(string='Data de inicio', required=True)
    time_experience = fields.Char(string='Período de experiência',required=True)
    food_subsidy = fields.Float(string="Subsídio de alimentação", default=0.0,required=True)
    transport_subsidy= fields.Float(string="Subsídio de Transporte", default=0.0,required=True)
    vacation_allowance=fields.Selection([('50','50%'),
                                         ('60', '60%'),
                                         ('70','70%'),
                                         ('80','80%'),
                                         ('90','90%'),
                                         ('100','100%')],
                                        string='Subsídio de férias', required=True)
    
    christmas_allowance= fields.Selection([('50','50%'),
                                         ('60', '60%'),
                                         ('70','70%'),
                                         ('80','80%'),
                                         ('90','90%'),
                                         ('100','100%')],
                                        string='Subsídio de Natal', required=True)
    
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    contract_type_id = fields.Many2one('hr.contract.type', "Tipo de Contrato", default=lambda self: self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_cdi', raise_if_not_found=False))    
    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._check_and_send_contract()
        return record

    def write(self, vals):
        result = super().write(vals)
        if 'stage_id' in vals:
            self._check_and_send_contract()
        return result

    def _check_and_send_contract(self):
        for rec in self:
            if rec.stage_id.name == 'Proposta de contrato':
                rec.action_generate_contract()

    
    #@api.onchange('stage_id')
    def action_generate_contract(self):
        if self.stage_id.name == 'Proposta de contrato':
            report = self.env.ref('ao_hr.action_contract_proposal_report')
            pdf_content, _ = report._render_qweb_pdf([self.id])
        
            if not pdf_content:
                raise UserError("Falha ao gerar o PDF da proposta de contrato.")
        
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            attachment = self.env['ir.attachment'].create({
                'name': 'Proposta de Contrato - %s.pdf' % self.name,
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'hr.applicant',
                'res_id': self.id,
                'mimetype': 'application/pdf',
            })

            if not self.email_from:
                raise UserError("O candidato não possui um e-mail registrado.")
        
            mail_values = {
                'subject': 'Proposta de Contrato',
                'body_html': '<p>Olá %s,<br/>Em anexo está sua proposta de contrato.</p>' % self.name,
                'email_to': self.email_from,
                'attachment_ids': [(6, 0, [attachment.id])],
            }

            error_message = False

            try:
                mail = self.env['mail.mail'].create(mail_values)
                mail.send()
            except Exception as e:
                error_message = f"Não foi possível enviar o email: {e}"

            # No fim (ou logo depois do erro), podes mandar uma notificação:
            if error_message:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Aviso',
                        'message': error_message,
                        'sticky': False,   # desaparece sozinho depois de alguns segundos
                        'type': 'warning', # cor amarela
                    }
                }

            
       
    def object_model(self):
        return self

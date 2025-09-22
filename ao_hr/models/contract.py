from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class ContractHr(models.Model):
    _inherit = 'hr.contract'

    name = fields.Char(string='Reference', required=True, readonly=True, default='New')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.contract.reference') or 'New'
        result = super(ContractHr, self).create(vals)
        return result

    def _get_time_left(self):
        for contract in self:
            duration = remaining = 0
            if contract.date_end:
                if contract.date_end >= fields.date.today():
                    if contract.date_end and contract.date_start:
                        remaining = (contract.date_end.year - datetime.today().year) * 12 + (
                                contract.date_end.month - datetime.today().month)
                contract.time_left = remaining
            else:
                contract.time_left = 6

    # def _get_time_left(self):
    #     for contract in self:
    #         duration = remaining = 0
    #         if contract.date_end:
    #             if contract.date_end >= fields.date.today():
    #                 if contract.date_start:
    #                     print("DATA FINAL ", contract.date_end)
    #                     remaining = (contract.date_end.year - datetime.today().year) * 12 + (
    #                             contract.date_end.month - datetime.today().month)
    #                     print('CALCULAAOD ', remaining)
    #
    #         contract.remaining_time = remaining
    hr_responsible_id = fields.Many2one('res.users', 'HR Responsible', tracking=True,
                                        help='Person responsible for validating the employee\'s contracts.')
    wage_final = fields.Float(compute='compute_wage_final', digits=(10, 2), string='Computed Wage')
    #teste = fields.Char(string="TESTANNNNDDDo")
    wage_hour = fields.Float(compute='compute_wage_hour', string='Hour Wage')
    wage_day = fields.Float(string="Wage Day ", compute="_compute_wage_day")
    week_hours = fields.Float(compute='compute_week_hours', string='Week Hours')
    remuneration_ids = fields.One2many('hr.remuneration', 'contract_id', string='Remunerations for this Contract', )
    exempt_irt = fields.Boolean(string="IRT", default=1)
    exempt_ss = fields.Boolean(string="SS", default=1)
    payslip_date = fields.Date(string="Last date payslip")
    first_work_day = fields.Integer(string="First Work Days")
    first_work_hours = fields.Integer(string="First Work Hours")
    has_bi = fields.Boolean("BI ?")
    bi = fields.Char("Nº BI")
    fiscal_number = fields.Char("Nº SS")
    has_taxpayer_card = fields.Boolean("Taxpayer card ?")
    has_medical_certificate = fields.Boolean("Medical Certificate ?")
    has_account_bank = fields.Boolean("Account Bank ?")
    has_household = fields.Boolean("Household ?")
    has_driving_license = fields.Boolean("Driving license?")
    diver_number = fields.Char("Driver Number")
    reason_termination = fields.Char("Reason Of Termination")
    utts = fields.Char('Utts')
    has_criminal_record = fields.Boolean("Criminal Record ?")
    has_certificates = fields.Boolean("Certificate ?")
    blacklist = fields.Boolean("Blacklist")
    #name = fields.Char('Contract Reference', required=False)
    check_period = fields.Boolean('Check period?', default="True", track_visibility='always')
    contract_period = fields.Selection(
        [('diary', 'Diary'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('semester', 'Semester'),
         ('yearly', 'Yearly')],
        'Paymente Cycle', track_visibility='always', default='yearly')
    contract_duration = fields.Integer('Duration (months)', track_visibility='always', default="6")
    contract_duration_infinity = fields.Integer('Duration (CDI)', default="80")
    time_left = fields.Integer('Left time', track_visibility='always', compute='_get_time_left')
    facade_time_left = fields.Integer('Left time', related='time_left')
    facade_date_end = fields.Date('End Date',
                                  help="End date of the contract (if it's a fixed-term contract).", related="date_end")

    # remaining_time = fields.Integer('Remaining time (months)', track_visibility='always', compute='_get_time_left')
    # facade_remaining_time = fields.Integer('Remaining time (months)', related='remaining_time')

    number_month = fields.Integer('Meses Restantes', compute='compute_number_month')
    number_duration_month = fields.Integer('Duração em Meses', compute='compute_number_duration_month')
    struct_id = fields.Many2one('hr.payroll.structure', 'Salary structure')

    car = fields.Boolean('Car?')
    phone = fields.Boolean('phone ?')
    chang = fields.Boolean('Recarga ?')
    home = fields.Boolean('Home?')
    description_alter_wage = fields.Text(string='Reason for salary change')

    @api.onchange('contract_type_id')
    def contract_type_onchange(self):
        if self.contract_type_id:
            if self.contract_type_id.code in ['CDI', 'CDD']:
                _structure_type = self.env['hr.payroll.structure.type'].search([('type', '=', 'employee')])
                self.structure_type_id = _structure_type
                self.struct_id = _structure_type.default_struct_id
                self.exempt_ss = True
            else:
                _structure_type = self.env['hr.payroll.structure.type'].search([('type', '=', 'worker')])
                self.structure_type_id = _structure_type
                self.struct_id = _structure_type.default_struct_id
                self.exempt_ss = False

    # @api.onchange('contract_duration')
    # def change_contract_duration(self):
    #     if self.contract_duration:
    #         # self.date_end = self.date_start + relativedelta(months=+self.contract_duration)
    #         self._get_time_left()
    #         self.compute_number_month()

    @api.onchange('contract_duration')
    def change_contract_duration(self):
        if self.contract_duration:
            self.date_end = self.date_start + relativedelta(months=+self.contract_duration)
            self._get_time_left()

    @api.onchange('date_start')
    def change_date_start(self):
        if self.contract_duration and self.date_start:
            self.date_end = self.date_start + relativedelta(months=+self.contract_duration)
            self._get_time_left()

    def _full_end_date(self):
        for res in self:
            res.date_end = res.date_start + relativedelta(months=+res.contract_duration)
            res._get_time_left()

    def _assign_open_contract(self):
        for contract in self:
            contract.employee_id.sudo().write({
                'contract_id': contract.id,
                'structure_type_id': contract.structure_type_id.id
            })

    def button_print_declaration(self):
        return self.env.ref('ao_hr.action_report_work_declaration').report_action(self)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            employee = record.employee_id
            if employee:
                record.has_bi = employee.has_bi
                record.has_taxpayer_card = employee.has_taxpayer_card
                record.has_medical_certificate = employee.has_medical_certificate
                record.has_household = employee.has_household
                record.has_driving_license = employee.has_driving_license
                record.has_criminal_record = employee.has_criminal_record
                record.has_certificates = employee.has_certificates
                record.blacklist = employee.blacklist
                record.bi = employee.identification_id
                record.fiscal_number = employee.social_security

    def compute_number_duration_month(self):
        for contract in self:
            duration = remaining = 0
            if contract.date_end:
                if contract.date_end >= contract.date_start:
                    if contract.date_end and contract.date_start:
                        remaining = (contract.date_end.year - contract.date_start.year) * 12 + (
                                contract.date_end.month - contract.date_start.month)
                    contract.number_duration_month = remaining
            else:
                contract.number_duration_month = 0

    def compute_week_hours(self):
        for contract in self:
            contract.week_hours = round(contract.resource_calendar_id.hours_per_week)

    def expiration_alert(self):
        print('********** start cron contract expiration ********* ')
        all_contracts = self.env['hr.contract'].search([('state', '=', 'open')])
        for contract in all_contracts:
            if contract:
                if contract.time_left <= 1:
                    if contract.date_end and contract.date_end >= fields.Date.today():
                        contract.sudo().create_message()
                        contract.sudo().send_mail_contract_alert()
                    if contract.date_end <= fields.Date.today():
                        contract.sudo().date_start = contract.sudo().date_end
                        contract.sudo().change_date_start()
                        contract.sudo()._get_time_left()
                        print('*********** Contract expired **** ')

    @api.depends('week_hours')
    def compute_wage_hour(self):
        for res in self:
            _week_hours = res.week_hours
            res.wage_hour = round((res.wage * 12) / (_week_hours * 52), 2)
            res._get_time_left()

    def compute_number_month(self):
        for contract in self:
            duration = remaining = 0
            if contract.date_end:
                if contract.date_end >= fields.date.today():
                    if contract.date_start:
                        remaining = (contract.date_end.year - datetime.today().year) * 12 + (
                                contract.date_end.month - datetime.today().month)
                    contract.number_month = remaining
                else:
                    contract.number_month = 0
            else:
                contract.number_month = 0

    @api.depends('resource_calendar_id')
    def _compute_wage_day(self):
        for res in self:
            _wage_day = res.wage_hour * res.resource_calendar_id.hours_per_day
            res.wage_day = _wage_day

    # @api.depends('first_work_day')
    # def _compute_first_work_hours(self):
    #     _hours = self.resource_calendar_id.day_hours
    #     self.first_work_hours = self.first_work_day * _hours

    def all_allowance(self):
        """
              07 - LEi 9.19 - Altera o Código do Imposto Sobre os Rendimentos de Trabalho e
              Revoga o Decreto que aprova a tabela de lucros minimos.
              :return: amount
              """
        amount = 0.0
        for res in self:
            for r in res.remuneration_ids:
                if (r.rem_type != 'deduction') and (r.date_start <= res.payslip_date):
                    if not r.date_end or (r.date_end >= res.payslip_date):
                        if r.remunerationcode_id.code in ['sub_fer', 'sub_learn', 'sub_learn_prod', 'sub_learn_ass', 'other_allowance']:
                            continue
                        if r.remunerationcode_id.code in ['sub_ali', 'sub_trans'] and r.amount <= 30000:
                            continue
                        if r.remunerationcode_id.code in ['sub_ali', 'sub_trans'] and r.amount > 30000:
                            amount += (r.amount - 30000)
                            continue
                        if r.remunerationcode_id.code in ['sub_fam']:
                            unsent_amount = (5 / 100) * res.wage
                            if r.amount > unsent_amount:
                                amount += (r.amount - unsent_amount)
                            continue
                        amount += r.amount
        return amount
    
    # def sub_fam_and_sub_proportional(self):
    #     #ISSO SAI
    #     pays_lip = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id)], limit=1)
    
    #     if not pays_lip:
    #         raise ValueError("Não foi encontrado um registro de Payslip associado.")
        
    #     return self.abo_fam_ss() + pays_lip.all_allowance_sub_proportional_vacation()

    def salarioiliquido(self):
        amount = 0.0
        for res in self:
            for r in res.remuneration_ids:
                if (r.rem_type != 'deduction')  and not r.remunerationcode_id.code in ['sub_fer', 'sub_proportional_vacation']:
                   if not r.date_end or (isinstance(r.date_end, (datetime.date, datetime.datetime)) and 
                                         isinstance(res.payslip_date, (datetime.date, datetime.datetime)) and r.date_end >= res.payslip_date):
                        if not r.date_end or (r.date_end >= res.payslip_date):
                            if r.remunerationcode_id.code:
                                amount += r.amount
                            
        return res.wage + amount
    
    def seguranca_social(self):
        return (3/100)*self.salarioiliquido()               
    
    def materia_coletavel(self):
        return self.net_salary() - self.seguranca_social()
       
    def net_salary(self):
        pays_lip = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id)], limit=1)
        bsesalary =0.0
        
        for res in self:
            bsesalary = res.wage
            
        netsalary = bsesalary + pays_lip.all_allowance() + self.abono_holiday()
        
        return netsalary   

    """PARA AS FÉRIAS DO IRT E MATÉRIA COLLECTÁVEL DO  INSS"""
    def all_allowance_absence_irt(self):
        """
        07 - LEi 9.19 - Altera o Código do Imposto Sobre os Rendimentos de Trabalho e
        Revoga o Decreto que aprova a tabela de lucros minimos.
        :return: amount
        """
        amount = 0.0
        for res in self:
            for r in res.remuneration_ids:
                if (r.rem_type != 'deduction') and (r.date_start <= res.payslip_date):
                    if not r.date_end or (r.date_end >= res.payslip_date):
                        if r.remunerationcode_id.code in ['sub_fer', 'sub_learn', 'sub_learn_prod', 'sub_learn_ass', ]:
                            continue
                        if r.remunerationcode_id.code in ['sub_learn']:
                            continue
                        if r.remunerationcode_id.code in ['sub_ali', 'sub_trans'] and r.amount <= 30000:
                            continue
                        if r.remunerationcode_id.code in ['sub_ali', 'sub_trans'] and r.amount > 30000:
                            amount += (r.amount - 30000)
                            print("Aqui =====", amount)
                        # amount += r.amount
                        # print("Agora ======", amount)
        return amount

    def gross_allowance(self):
        """
        07 - LEi 9.19 - Altera o Código do Imposto Sobre os Rendimentos de Trabalho e
        Revoga o Decreto que aprova a tabela de lucros minimos.
        :return: amount
        """
        amount = 0.0
        for res in self:
            for r in res.remuneration_ids:
                if res.payslip_date:
                    if (r.rem_type != 'deduction') and (r.date_start <= res.payslip_date):
                        if not r.date_end or (r.date_end >= res.payslip_date):
                            amount += r.amount
                else:
                    if r.rem_type != 'deduction':
                        if not r.date_end:
                            amount += r.amount
        return amount

    def net_allowance(self):
        """
              :return: amount
              """
        amount = 0.0
        for res in self:
            for r in res.remuneration_ids:
                if (r.rem_type == 'deduction') and (r.date_start <= res.payslip_date):
                    if not r.date_end or (r.date_end >= res.payslip_date):
                        amount += r.amount
        net_wage = self.gross_allowance() - amount
        return net_wage

    #
    def abo_fam_ss(self):
        """
               IRT, VAI SUPORTAR
               ABONO FAMILIAR MAIOR QUE 5% DO VALOR BASE
               :return: amount
               """
        for res in self:
            for r in res.remuneration_ids:
                if r.remunerationcode_id.code in ['sub_fam'] and (r.date_start <= res.payslip_date):
                    if not r.date_end or (r.date_end >= res.payslip_date):
                        unsent_amount = (5 / 100) * res.wage
                        if r.amount > unsent_amount:
                            return r.amount - unsent_amount
            return 0.0

    def abono_fam_inss(self):
        for res in self:
            _s = 0.0
            print(res.remuneration_ids)
            for r in res.remuneration_ids:
                print(r.remunerationcode_id.code)
                if r.remunerationcode_id.code in ['sub_fam'] and (r.date_start <= res.payslip_date):
                    if not r.date_end or (r.date_end >= res.payslip_date):
                        _s = r.amount
            return _s

    def abono_holiday(self):
        for res in self:
            _s = 0.0
            for r in res.remuneration_ids:
                if r.remunerationcode_id.code in ['sub_fer', 'sub_proportional_vacation'] and (r.date_start <= res.payslip_date):
                    if not r.date_end or (r.date_end <= res.payslip_date):
                        _s = r.amount
            return _s


    #

    # @api.depends('date_start', 'payslip_date')
    # def _compute_period_working_days(self):
    #     # TODO Add code to consider public holidays
    #     if self.date_start and self.payslip_date:
    #         schedule = self.sudo().resource_calendar_id
    #         total_days = 0
    #         if self.date_start[:7] == self.payslip_date[:7]:
    #             date_from = fields.Date.from_string(self.date_start)
    #             date_to = fields.Date.from_string(self.payslip_date)
    #             delta_days = (date_to - date_from).days
    #             for single_date in (date_from + timedelta(n) for n in range(delta_days + 1)):
    #                 if schedule._is_work_day(single_date, schedule.id):
    #                     total_days += 1
    #             self.first_work_day = total_days

    def create_message(self):
        message_id = self.env['mail.message']
        partner_root = self.env['ir.model.data'].search([('name', '=', 'partner_root'), ('module', '=', 'base')])
        odoo_boot = self.env['res.partner'].sudo().search([('id', '=', partner_root.res_id), ('active', '=', False)])
        vals = {
            'email_from': odoo_boot.email,
            'author_id': odoo_boot.id,
            'message_type': 'comment',
            'moderation_status': 'accepted',
            'reply_to': odoo_boot.email,
            'subtype_id': 1,
            'model': 'mail.channel',
            'channel_ids': [(6, 0, self.create_partners_channel().ids)],
            'body': 'O contrato n. %s, do funcionario %s, esta quase a expirar' % (self.name, self.employee_id.name)

        }
        res = message_id.sudo().create(vals)
        return res

    def send_mail_contract_alert(self):
        self.ensure_one()
        template_id = self.env.ref('ao_hr.contract_mail_template').id
        self.env['mail.template'].browse(template_id).send_mail(self.id, force_send=True)

    def create_partners_channel(self):
        partner_root = self.env['ir.model.data'].search([('name', '=', 'user_root'), ('module', '=', 'base')])
        odoo_boot = self.env['res.users'].sudo().search([('id', '=', partner_root.res_id), ('active', '=', False)])
        channel_name = '%s, %s' % (odoo_boot.partner_id.name, self.employee_id.name)
        channel = self.env['mail.channel']
        res = self.env['mail.channel']

        if self.state == 'open':
            if not channel.sudo().search([('name', '=', channel_name)]):
                vals = {
                    'channel_last_seen_partner_ids': [(4, partner_id) for partner_id in
                                                      [self.employee_id.user_partner_id.id, odoo_boot.partner_id.id]],
                    'public': 'private',
                    'channel_type': 'chat',
                    'email_send': False,
                    'name': channel_name,
                }
                res = channel.sudo().create(vals)
            else:

                res = channel.sudo().search([('name', '=', channel_name)])
        return res


class HrContractType(models.Model):
    _inherit = 'hr.contract.type'

    code = fields.Char('Code')


class HrContratHistory(models.Model):
    _inherit = 'hr.contract.history'
    _s = 0.0

    def percentage_value(self):
        for rec in self:
            if rec.contract_ids:
                _s = float((1 - rec.wage / rec.contract_ids[0].wage) * -100)
                return str(round(_s, 2)) + " % "
        return str(0.0) + " % "

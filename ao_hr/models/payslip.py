import time
from psycopg2 import sql
from datetime import datetime, timedelta, time
from datetime import time as datetime_time
from pytz import timezone
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models,_, tools
from odoo.exceptions import UserError, ValidationError
import calendar
from . import utils
import base64
from odoo.tools.safe_eval import safe_eval
 

class Payslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_leave_entry_lines(self, contract=None):
        leave_type = ['ATRA', 'FJNR', 'FJR', 'FI']
        leave_data = []
        for type in leave_type:
            leave = self.env['hr.leave'].search(
                [('holiday_status_id.code', '=', type),
                 ('employee_id.contract_id', '=', contract.id), '&', ('state', '=', 'validate'),
                 ('payslip_state', '=', 'done')])
            if leave:
                work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
                attendance_line = {
                    'name': type,
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_days': sum([rec.number_of_days for rec in leave]),
                    'number_of_hours': sum([rec.number_of_hours_display for rec in leave]),
                    'amount': -1 * (sum([rec.number_of_hours_display for rec in leave]) * self.contract_id.wage_hour)
                }
                leave_data.append(attendance_line)
        return leave_data

    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        res = []
        print(" *************************** ATTENDANCE ************************************")

        hours_per_day = self._get_worked_day_lines_hours_per_day()
        work_hours = self.contract_id._get_work_hours(self.date_from, self.date_to, domain=domain)
        work_hours_ordered = sorted(work_hours.items(), key=lambda x: x[1])
        biggest_work = work_hours_ordered[-1][0] if work_hours_ordered else 0
        add_days_rounding = 0
        for work_entry_type_id, hours in work_hours_ordered:
            work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
            days = round(hours / hours_per_day, 5) if hours_per_day else 0
            if work_entry_type_id == biggest_work:
                days += add_days_rounding
            day_rounded = self._round_days(work_entry_type, days)
            add_days_rounding += (days - day_rounded)
            attendance_line = {
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_type_id,
                'number_of_days': day_rounded,
                'number_of_hours': hours,
            }
            res.append(attendance_line)
        return res

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """
        :returns: a list of dict containing the worked days values that should be applied for the given payslip
        """
        print(" *************************** Get worked day Lines ************************************")
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        contract = self.contract_id
        leave_lines = self._get_leave_entry_lines(contract)
        if contract.resource_calendar_id:
            res = self._get_worked_day_lines_values(domain=domain)
            if not check_out_of_contract:
                return res

            # If the contract doesn't cover the whole month, create
            # worked_days lines to adapt the wage accordingly
            out_days, out_hours = 0, 0
            reference_calendar = self._get_out_of_contract_calendar()
            if self.date_from < contract.date_start:
                start = fields.Datetime.to_datetime(self.date_from)
                stop = fields.Datetime.to_datetime(contract.date_start) + relativedelta(days=-1, hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False,
                                                                     domain=['|', ('work_entry_type_id', '=', False), (
                                                                         'work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']
            if contract.date_end and contract.date_end < self.date_to:
                start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(days=1)
                stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False,
                                                                     domain=['|', ('work_entry_type_id', '=', False), (
                                                                         'work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']

            if out_days or out_hours:
                work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
                res.append({
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_days': out_days,
                    'number_of_hours': out_hours,
                })
                res.extend(leave_lines)
        return res
    
    def action_send_email(self):
        sem_email = []
        msg = ""
        for payslip in self:
            if payslip.net_wage == 0.0:
                continue
        
            if not payslip.employee_id.work_email:
                sem_email.append(payslip.employee_id.name)
                
            report = self.env.ref('ao_hr.action_report_simple_payslip')
            pdf_content, _ = report._render_qweb_pdf([payslip.id])
            pdf_base64 = base64.b64encode(pdf_content)

            attachment = self.env['ir.attachment'].create({
                'name': f'Recibo_{payslip.employee_id.name}.pdf',
                'type': 'binary',
                'datas': pdf_base64,
                'mimetype': 'application/pdf',
                'res_model': False,
                'res_id':False,
            })

            mail_values = {
                'subject': f'Recibo de Vencimento - {payslip.employee_id.name}',
                'body_html': f"""
                    <p>Melhores cumprimentos {payslip.employee_id.name},</p>
                    <p>Remeto em anexo o recibo de vencimento para assinatura.</p>
                    <p>Atenciosamente,<br/>RH</p>
                """,
                'email_to': payslip.employee_id.work_email,
                'attachment_ids': [(6, 0, [attachment.id])],
            }

            try:
                mail = self.env['mail.mail'].create(mail_values)
                mail.send()
            except Exception as e:
                raise UserError(f"Não foi possível enviar o email para {payslip.employee_id.name}: {e}")
        
#         return sem_email
            
        if sem_email:
            msg = (
            "Não foi possível enviar e-mail para os seguintes funcionários:\n- "
            + "\n- ".join(sem_email)
            + "\n\nPode ser pelas seguintes razões:\n"
            "- O e-mail pode estar errado ou não foi inserido\n"
            "- O servidor de e-mail pode não estar ativo\n"
             "- Má configuração do servidor SMTP\n "
            "- Verifique se há acesso à internet"
)
            
            raise UserError(f""+msg)

    def compute_remuneration(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code == 'BAS':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.remuneration = _sum
        return res

    def compute_overtimes(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code == 'HEXTRA':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.overtimes = _sum
        return res

    def compute_extra_remunerations(self):
        for payslip in self:
            payslip.extra_remuneration = payslip.total_remunerations - payslip.remuneration - payslip.overtimes

    def compute_misses(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code == 'FALTA':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.misses = _sum
        return res

    def compute_remuneration_inss_base(self):
        for slip in self:
            slip.remuneration_inss_base = slip.remuneration + slip.overtimes + slip.misses + slip.allowance

    def compute_remuneration_inss_extra(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code in ('ABOINSS', 'ABOINSSIRT'):
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.remuneration_inss_extra = _sum
        return res

    def _compute_allowances(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if not line.appears_on_payslip:
                    continue
                if line.category_id.code in ('ABO', 'ALW', 'OTHERS_SUJ'):
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.allowance = _sum
        return res

    def compute_remuneration_inss_total(self):
        for slip in self:
            slip.remuneration_inss_total = slip.remuneration_inss_base + slip.remuneration_inss_extra

    def compute_amount_inss(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code == 'INSS':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.amount_inss = _sum
        return res

    def compute_amount_irt(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code == 'IRT':
                    _sum = line.total
            res[slip.id] = _sum
            slip.amount_irt = _sum
        return res

    def compute_extra_deductions(self):
        for payslip in self:
            _sum = 0.0
            for line in payslip.line_ids:
                if line.category_id.code in ['DED']:
                    _sum = _sum + line.deduction
            payslip.extra_deductions = -_sum

    def compute_amount_base_irt(self):
        res = {}
        for slip in self:
            _sum = 0.0
            excesso_sub_ali_trans = 0.0
            _has_irt = False
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code in ('BAS', 'HEXTRA', 'FALTA', 'GRAT', 'GRATS') or line.code in ('sub_ali',
                                                                                                         'sub_trans'):
                    _sum = _sum + line.total
                    if line.code in ('sub_ali', 'sub_trans'):
                        # Se o valor ultrapassar 30.000, armazene o excesso para descontar na SS
                        if line.total > 30000:
                            excesso_sub_ali_trans += line.total - 30000
                if line.category_id.code in ['IRT']:
                    _has_irt = True
            res[slip.id] = _sum
            ss_collect = ((_sum + slip.all_allowance() - excesso_sub_ali_trans) * (3 / 100)) if _has_irt else 0.0
            k = (_sum + slip.all_allowance() + slip.all_allowance_sub_proportional_vacation())
            slip.amount_base_irt = _sum + slip.all_allowance() + slip.all_allowance_sub_proportional_vacation() - ss_collect

            if slip.struct_id.code in ["BASE", "CLASS_A"]:
                slip.amount_base_irt = _sum + slip.all_allowance() - ss_collect - slip.sub_ali - slip.sub_trans
                print("Somatório:", slip.amount_base_irt)
            elif slip.struct_id.code in ["CLASS-B", "CLASS_B"]:
                slip.amount_base_irt = slip.total_remunerations - slip.misses
        return res

    def all_allowance_sub_proportional_vacation(self):
        """
        07 - LEi 9.19 - Altera o Código do Imposto Sobre os Rendimentos de Trabalho e
        Revoga o Decreto que aprova a tabela de lucros minimos.
        :return: amount
        """
        amount = 0.0
        for res in self:
            for r in res.contract_id.remuneration_ids:
                if (r.rem_type != 'deduction'):
                    if not r.date_end:
                        if r.remunerationcode_id.code in ['sub_proportional_vacation']:
                            return r.amount
        return 0.0

    def all_allowance(self):
        """
        07 - LEi 9.19 - Altera o Código do Imposto Sobre os Rendimentos de Trabalho e
        Revoga o Decreto que aprova a tabela de lucros minimos.
        :return: amount
        """
        amount = 0.0
        for res in self:
            for r in res.contract_id.remuneration_ids:
                if (r.rem_type != 'deduction') and (r.date_start <= res.date_to):
                    if not r.date_end or (r.date_end >= res.date_to):
                        if r.remunerationcode_id.code in ['sub_fer', 'sub_proportional_vacation','sub_learn', 'sub_learn_prod', 'sub_learn_ass']:
                            continue
                        if r.remunerationcode_id.code in ['sub_learn']:
                            continue
                        if r.remunerationcode_id.code in ['sub_ali', 'sub_trans'] and r.amount <= 30000:
                            continue
                        if r.remunerationcode_id.code in ['sub_ali', 'sub_trans'] and r.amount > 30000:
                            amount += (r.amount - 30000)
                            continue
                        if r.remunerationcode_id.code in ['sub_fam']:
                             unsent_amount = (5 / 100) * res.contract_id.wage
                             if r.amount > unsent_amount:
                                 amount += (r.amount - unsent_amount)

                             continue
                        amount += r.amount
        
        return amount

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

    def _amount_irt_exempt(self):
        """Used in irt report"""
        amount = 0.0
        for res in self:
            for line in res.line_ids:
                if line.code in ['sub_ali', 'sub_trans'] and line.amount <= 30000:
                    amount += line.amount
                if line.code in ['sub_ali', 'sub_trans'] and line.amount > 30000:
                    amount += line.amount - (line.amount - 30000)
        return amount

    def compute_payslip_period(self):
        res = {}
        for slip in self:
            date_obj = datetime.strptime(str(slip.date_from), '%Y-%m-%d')
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
            # return months[int(date_obj.month)]
            slip.payslip_period = months[int(date_obj.month)]

    def compute_total_remunerations(self):
        res = {}
        for slip in self:
            rem_total = 0.0
            for slip_line in slip.line_ids:
                if slip_line.code not in ['GROSS', 'NET']:
                    if not slip_line.appears_on_payslip:
                        continue
                    rem_total += slip_line.remuneration
            res[slip.id] = rem_total
            #slip.total_remunerations = rem_total
            #print("TOTAL NA PAYSLIP: ", rem_total)
            slip.total_remunerations = rem_total
        return res

    def compute_total_deductions(self):
        ded_total = 0.0
        for slip in self:
            ded_total = 0.0
            for slipline in slip.line_ids:
                if slipline.code not in ['GROSS', 'NET', 'sub_learn']:
                    if not slipline.appears_on_payslip:
                        continue
                    if slipline.code != 'ss_collect':
                        if slipline.amount < 0:
                            ded_total += abs(slipline.amount)
            # res[slip.id] = ded_total
            #slip.total_deductions = ded_total
            slip.total_deductions = ded_total
        return ded_total

    def compute_total_paid(self):
        for slip in self:
            slip.total_paid = slip.total_remunerations - slip.total_deductions

    @api.depends('contract_id')
    def _compute_period_working_days(self):
        for payslip in self:
            # TODO Add code to consider public holidays
            total_days = 0.0
            if payslip.contract_id:
                for line in payslip.worked_days_line_ids:
                    if line.code == 'WORK100':
                        total_days += line.number_of_days
                payslip.period_working_days = total_days

    def compute_sub_ali(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.code == 'sub_ali':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.sub_ali = _sum
        return res

    def compute_sub_fam(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.code == 'sub_fam':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.sub_fam = _sum
        return res

    def compute_sub_trans(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.code == 'sub_trans':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.sub_trans = _sum
        return res

    def compute_total_sub_other(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.code not in ['sub_ali', 'sub_trans', 'sub_fam', 'GROSS', 'NET'] and line.category_id.code in ['ABO', 'GRAT','GRATS', 'HEXTRA', 'SOC', 'OTHERS_SUJ', 'OTHERS', 'ALW']:
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.total_sub_other = _sum
        return res

    sub_ali = fields.Float('Sub.Alim', digits=(10, 2), compute="compute_sub_ali")
    sub_trans = fields.Float('Sub.Trans', digits=(10, 2), compute="compute_sub_trans")
    sub_fam = fields.Float('Sub.Fam', digits=(10, 2), compute="compute_sub_fam")
    total_sub_other = fields.Float('Sub.Others', digits=(10, 2), compute="compute_total_sub_other")
    allowance = fields.Float(string="Allowances", digits=(10, 2), compute='_compute_allowances')
    remuneration = fields.Float(compute="compute_remuneration", digits=(10, 2), string='Remuneration',
                                help='This is the Wage amount')
    overtimes = fields.Float(compute="compute_overtimes", digits=(10, 2), string='Overtimes',
                             help='This is the total amount for Overtimes')
    extra_remunerations = fields.Float(compute="compute_extra_remunerations", digits=(10, 2),
                                       string='Extra Remuneration')
    misses = fields.Float(compute=compute_misses, digits=(10, 2), string='Misses',
                          help='This is the total discount for misses')
    remuneration_inss_base = fields.Float(compute="compute_remuneration_inss_base", digits=(10, 2),
                                          string='Base INSS',
                                          help='This is the INSS base amount')
    remuneration_inss_extra = fields.Float(compute="compute_remuneration_inss_extra", digits=(10, 2),
                                           string='Extra INSS Remuneration',
                                           help='Those are other INSS collectible remunerations')
    remuneration_inss_total = fields.Float(compute="compute_remuneration_inss_total", digits=(10, 2),
                                           string='Gross Remuneration')
    amount_inss = fields.Float(compute=compute_amount_inss, digits=(10, 2), string='INSS Amount')
    amount_irt = fields.Float(compute=compute_amount_irt, digits=(10, 2), string='IRT Amount')
    extra_deductions = fields.Float(compute="compute_extra_deductions", digits=(10, 2), string='Extra Deduction')
    amount_base_irt = fields.Float(compute="compute_amount_base_irt", digits=(10, 2), string='Base IRT')
    period_working_days = fields.Integer(compute='_compute_period_working_days', string='Payslip Days')
    payslip_period = fields.Char(compute=compute_payslip_period, string='Payslip Period')
    total_remunerations = fields.Float(compute="compute_total_remunerations", digits=(10, 2),
                                       string='Total of Remunerations')
    total_deductions = fields.Float(compute="compute_total_deductions", digits=(10, 2), string='Total of Deductions')
    total_paid = fields.Float(compute="compute_total_paid", digits=(10, 2), string='Total Paid')
    amount_ded = fields.Float(compute='_compute_amount_ded')
    abono_fam = fields.Float(compute='_compute_abono_fam', string='Remuneration Family')
    sub_holiday = fields.Float(compute='_compute_ferias')
    employee_name = fields.Char(string='Employee Name', compute='_compute_employee_name', store=True)

    # hasLeavesOrOvertime = fields.Boolean(compute=compute_hasLeavesOrOvertime, string='Exists Leaves or Overtime')
    # leave_ids = fields.One2many('hr.payslip.leaves', 'leave_id',string='Leaves',copy=True)
    @api.depends('employee_id')
    def _compute_employee_name(self):
        for rec in self:
            rec.employee_name = rec.employee_id.name if rec.employee_id else False

    def _compute_ferias(self):
        for rec in self:
            if rec.contract_id:
                rec.sub_holiday = rec.contract_id.abono_holiday()
            else:
                rec.sub_holiday = 0.0

    def _compute_basic_net(self):
        for payslip in self:
            payslip.basic_wage = payslip._get_salary_line_total('BASE')
            payslip.net_wage = payslip.total_paid

    def _compute_abono_fam(self):

        for rec in self:
            if rec.contract_id:
                rec.abono_fam = rec.contract_id.abono_fam_inss()
            else:
                rec.abono_fam = 0.0

    def compute_sheet(self):
        super(Payslip, self).compute_sheet()
        self.net_allowance()
        self.gross_allowance()

    def net_allowance(self):
        for res in self:
            for line in res.line_ids:
                if line.code in ['NET']:
                    line.amount = res.total_paid

    def gross_allowance(self):
        _CODE = ('IRT', 'INSS', 'INSSCOLLECT', 'NET', 'FALTA', 'DED')
        for res in self:
            for line in res.line_ids:
                if line.code in ['GROSS']:
                    line.amount = 0.0
                    line.amount = sum([item.amount for item in res.line_ids if item.category_id.code not in _CODE])

    def _compute_amount_ded(self):
        for res in self:
            _CODE = ('DES_ALI', 'DES_ADI')
            # _total = sum([line.total for line in res.details_by_salary_rule_category if line.code in _CODE]) * -1
            _total = 0
            res.amount_ded = _total

    def action_payslip_draft(self):
        for res in self:
            res.write({'state': 'draft'})

    def action_print_payslip(self):
        return self.env.ref('ao_hr.action_report_simple_payslip').report_action(self)


class PayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda l: l.env.user.company_id)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type")
    budget = fields.Float(string="Budget", compute='_compute_total_payable')
    irt_amount_total = fields.Float(string="Total IRT", compute='_compute_total_payable')
    ss_amount_total = fields.Float(string="Total SS", compute='_compute_total_payable')

    salary_map_xls = fields.Binary('Salary Map XLS')
    payment_map_xls = fields.Binary('Payment Map XLS')
    payment_map_xls_filename = fields.Char("Nome do ficheiro do Mapa Bancário")
    
    def _compute_total_payable(self):
        for rec in self:
            rec.budget = sum([r.total_paid for r in rec.slip_ids])
            rec.irt_amount_total = sum([abs(r.amount_irt) for r in rec.slip_ids])
            rec.ss_amount_total = sum([abs(r.amount_inss) for r in rec.slip_ids])

    def action_send_email(self):
        sem_email_total = []
        for run in self:
            if not run.slip_ids:
                raise UserError(_("Não há recibos de salário associados a esta folha de pagamento."))
            
            payslips = run.slip_ids  
            for payslip in payslips:
                if not payslip.employee_id.work_email:
                    sem_email_total.append(payslip.employee_id.name)
                    continue
                payslip.action_send_email()
        if sem_email_total:
            msg = (
            "Não foi possível enviar e-mail para os seguintes funcionários:\n- "
            + "\n- ".join(set(sem_email_total))
            + "\n\nPode ser pelas seguintes razões:\n"
            "- O e-mail pode estar errado ou não foi inserido\n"
            "- O servidor de e-mail pode não estar ativo\n"
            "- Má configuração do servidor SMTP\n "
            "- Verifique se há acesso à internet"
            )
            raise UserError(msg)

    def recalculate_sheet(self):
        for slip in self.slip_ids:
            if slip.state in ['draft', 'verify']:
                slip.compute_sheet()

    def generate_payment_partner_xls(self):
        payment_map_data = []
        payment = {
            "rows": [],
            "info": {
                "create_date": f"{self.create_date.day}-{self.create_date.month}-{self.create_date.year}",
                "reference": self.name
            }
        }
        payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', self.id)])
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
                'batch': self.name,
                'order': f"ORD {meses[self.create_date.month]}",
                'bank': 'LUANDA',
                'iban': slip.employee_id.bank_iban,
                'valor': slip.total_paid
            }
            payment_map_data.append(res)
        payment['rows'] = payment_map_data
        
        return payment

    def generate_salary_map_xls(self):
        salary_map_data = []
        payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', self.id)])
        order_number = 0
        for slip in payslips:
            order_number += 1
            wage_and_allowance = slip.contract_id.wage + slip.allowance
            res = {
                'n': order_number,
                'name': slip.employee_id.name,
                'wage': slip.contract_id.wage,
                'departament': slip.contract_id.department_id.name,
                'job': slip.contract_id.job_id.name,
                'n_ss': slip.contract_id.fiscal_number,
                'desc_faltas': slip.contract_id.fiscal_number,
                'sub_ali': sum(line.total for line in slip.line_ids if line.code == 'sub_ali'),
                'sub_trans': sum(line.total for line in slip.line_ids if line.code == 'sub_trans'),
                'sub_fam': sum(line.total for line in slip.line_ids if line.code == 'sub_fam'),
                'sub_nat': sum(line.total for line in slip.line_ids if line.code == 'sub_nat'),
                'sub_ferias': sum(line.total for line in slip.line_ids if line.code == 'SF'),
                'total_sub': slip.allowance,
                'gross_salary': slip.total_remunerations,
                'ss_tax': sum(line.total for line in slip.line_ids if line.category_id.code == 'INSS') * -1,
                'rem_tribut': 0.0,
                'irt': sum(line.total for line in slip.line_ids if line.category_id.code == 'IRT') * -1,
                'salary_advance': sum(line.total for line in slip.line_ids if line.code == 'SAR'),
                'loan': sum(line.total for line in slip.line_ids if line.code == 'LO'),
                'fact_saude': 0.0,
                'outros_desc': 0.0,
                'total_deductions': slip.total_deductions,
                'percentage': ((slip.total_deductions / wage_and_allowance) / 100),
                'net_salary': slip.total_paid,
            }
            salary_map_data.append(res)
        return salary_map_data

    def print_salary_map_xlsx(self):
        salary_map = self.generate_salary_map_xls()
        utils.generate_xls(salary_map, self.name)
        self.salary_map_xls = base64.b64encode(utils.read_xls())

    def print_payment_bank_map_xlsx(self):
        # Isto pode ser substituído depois por self.generate_payment_partner_xls()
        payment_map = self.generate_payment_partner_xls()

        # Importa do ficheiro de utils ou chama direto aqui
        xls_content = utils.generate_bank_sheet(payment_map, self.company_id)

        self.payment_map_xls = xls_content
        self.payment_map_xls_filename = f"{self.name}_mapa_pagamento.xlsx"

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model=hr.payslip.run&id={self.id}&field=payment_map_xls&filename_field=payment_map_xls_filename&download=true",
            'target': 'new',
        }


class PayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def compute_remuneration(self):
        total = 0
        for slip_line in self:
            if slip_line.total >= 0:
                total = slip_line.total
            else:
                total = 0
            slip_line.remuneration = total
        return total

    def compute_deduction(self):
        total = 0
        for slip_line in self:
            if slip_line.total < 0:
                total = abs(slip_line.total)
            else:
                total = 0
            slip_line.deduction = total

        return total

    remuneration = fields.Float(compute=compute_remuneration, digits=(10, 2), string='Remuneration')
    deduction = fields.Float(compute=compute_deduction, digits=(10, 2), string='Deduction')
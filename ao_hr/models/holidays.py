from odoo import fields, models, api
import base64
import logging


_logger = logging.getLogger(__name__)

class HolidaysStatus(models.Model):
    _inherit = 'hr.leave.type'

    code = fields.Char('Code', size=6, help='Type here a code for this Holiday Type')


class Holidays(models.Model):
    _inherit = 'hr.leave'
    sf_start = fields.Date('Date From')
    sf_end = fields.Date('Date To')
    leave_type_code = fields.Char('Type Code')
    disc_ali_trans = fields.Boolean(string="Discount on food and transport allowance ?", default=0)
    job_id = fields.Many2one('hr.job', string="Job Position")
        
    @api.onchange('date_from', 'date_to')
    def onchange_date_from_and_to(self):
        self.sf_end = self.date_to
        self.sf_start = self.date_from

    @api.onchange('holiday_status_id')
    def onchange_type_holidays(self):
        if self.holiday_status_id:
            self.leave_type_code = self.holiday_status_id.code
            self.disc_ali_trans = True if self.holiday_status_id.code == 'SF' else False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.manager_id = self.employee_id and self.employee_id.parent_id
        self.department_id = self.employee_id.department_id
        self.job_id = self.employee_id.job_id
        self._compute_number_of_days()

        # # TODO enable in enterprise
        # self._onchange_date_from()
        # self._onchange_date_to()

    def action_approve(self):
        res = super(Holidays, self).action_approve()
        report = self.env.ref('ao_hr.action_vacation_requeste_report')
        
        for leave in self:
            if leave.payslip_state != False and leave.holiday_status_id.code in ['SF']:
                remuneration = self.env['hr.remuneration.code'].search([('code', '=', 'sub_fer')], limit=1)
                remuneration_line_fields = [(0, 0, {
                    'remunerationcode_id': remuneration.id,
                    'name': remuneration.name,
                    'date_start': leave.sf_start,
                    'date_end': leave.sf_end,
                    'rem_type': 'remuneration',
                    'amount': leave.employee_id.contract_id.wage / 2
                })]
                leave.employee_id.contract_id.remuneration_ids = remuneration_line_fields
                attachment =  self.generate_vacation_guide(report,leave)
                self.send_to_email(attachment, leave.employee_id)
                
        return res

    def generate_vacation_guide(self,report, leave):
        pdf_content, _ = report._render_qweb_pdf([leave.id])

        attachment = self.env['ir.attachment'].create({
                    'name': f"Guia de Férias - {leave.employee_id.name}",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'hr.leave',
                    'res_id': leave.id,
                    'mimetype': 'application/pdf',
                })
        return attachment
    
    def send_to_email(self, attachment, employee):
        employee = self.env['hr.employee'].browse(employee.id)

        if employee and employee.work_email:
            mail_values = {
                'subject': 'Guia de Férias',
                'body_html': f'''
                    <p>Caro(a) colaborador(a),</p>
                    <p>Esperamos que este e-mail o encontre bem.</p>
                    <p>Em anexo está a sua guia de férias.</p>
                    <p>Atenciosamente,<br/>RH</p>
                ''',
                'email_to': employee.work_email,
                'attachment_ids': [(6, 0, [attachment.id])],
            }
            try:
                mail = self.env['mail.mail'].create(mail_values)
                mail.send()
            except Exception as e:
                _logger.error(f"Erro ao enviar email para {employee.name} ({employee.work_email}): {e}")
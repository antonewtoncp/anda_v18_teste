from odoo import models, fields, api
from odoo.exceptions import UserError

class WizardAbsenceMap(models.TransientModel):
    _name = "wizard.absence.map"
    _description = "Assistente do Mapa de Ausência"

    date_from = fields.Date(string="Data de Início", required=True)
    date_to = fields.Date(string="Data de FIm", required=True)
    leave_type_id = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Tipo de Ausência",
        required=False,
        help="Filtrar pelo tipo de ausência"
    )

    def action_generate_report(self):
        domain = []
        
        if self.leave_type_id:
            domain = [
            ('holiday_status_id', '=', self.leave_type_id.id),
            ('sf_start', '>=', self.date_from),
            ('sf_end', '<=', self.date_to),
            ('state', '=', 'validate')
        ]
        else:
            domain = [
            ('sf_start', '>=', self.date_from),
            ('sf_end', '<=', self.date_to),
            ('state', '=', 'validate')
         ]
        
        leaves = self.env['hr.leave'].search(domain,order='sf_start asc')

        docs = []
        others=[]
        if not leaves:
            raise UserError(("Não existe nenhum dados para o tipo de ausência."))
    
        for leave in leaves:
            docs.append({
            'start_date': leave.sf_start.strftime('%Y-%m-%d') if leave.sf_start else '',
            'end_date': leave.sf_end.strftime('%Y-%m-%d') if leave.sf_end else '',
            'leave_type': leave.holiday_status_id.name or '',
            'duration':leave.number_of_days,
            'state': leave.state or '',
            'employee': leave.employee_id.name or '',
        })
        others.append({
            'start':self.date_from,
            'end':self.date_to,
            'type': self.leave_type_id.name if self.leave_type_id else 'Todas',
        })
            
        return self.env.ref('ao_hr.absence_map_pdf').report_action(self, data={'docs': docs, 'others':others})

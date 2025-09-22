from odoo import models

class ReportAbsenceMap(models.AbstractModel):
    _name = 'report.ao_hr.absence_map_template'
    _description = 'Relatório de Mapa de Ausência'

    def _get_report_values(self, docids, data=None):
        docs = data.get('docs', []) if data else []
        return {
            'doc_ids': docids,
            'doc_model': 'wizard.absence.map',
            'data': data or {},
            'docs': docs,
        }

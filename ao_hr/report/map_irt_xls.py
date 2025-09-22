from odoo import models


class MapXlsx(models.AbstractModel):
    _name = 'report.ao_hr.report.irt.xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, model):
        # Create a new worksheet
        sheet = workbook.add_worksheet('Declaração Modelo 2')

        # Define formats
        title_format = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True})
        header_format = workbook.add_format({
            'font_size': 12,
            'align': 'center',
            'bold': True,
            'border': 1,
            'bg_color': '#2f75b5',
            'font_color': '#FFFFFF'
        })
        data_format = workbook.add_format({'font_size': 10, 'align': 'center', 'border': 1})
        number_format = workbook.add_format({'font_size': 10, 'align': 'center', 'border': 1, 'num_format': '#,##0.00'})

        # Set column widths for better readability
        sheet.set_column(0, 0, 20)  # Column (ID)
        sheet.set_column(1, 0, 20)  # Column (NIF)
        sheet.set_column(2, 1, 30)  # Column (NOME)
        sheet.set_column(3, 2, 40)  # Column (SEGURANÇA SOCIAL)
        sheet.set_column(4, 3, 40)  # Column (SEGURANÇA SOCIAL)
        sheet.set_column(5, 5, 30)  # Column (REND. SUJEITO)
        sheet.set_column(6, 6, 30)  # Column (REND. NÃO SUJEITO)
        sheet.set_column(7, 6, 20)  # Column (INSETOS)
        sheet.set_column(8, 6, 30)  # Column (IMPOSTO PAGO)
        sheet.set_column(9, 6, 30)  # Column (Transporte)
        sheet.set_column(10, 6, 30) # Column (Abono)
        sheet.set_column(11, 6, 30) # Column (Reembolso)
        sheet.set_column(12, 6, 30) # Column (Outros)
        sheet.set_column(13, 6, 30) # Column (Calculo Manual de Excesso de Subsídios?)
        sheet.set_column(14, 6, 30) # Column (Excesso Subsídios Não Sujeitos)
        sheet.set_column(15, 6, 30) # Column (Abono Falhas)
        sheet.set_column(16, 6, 30) # Column (Subsídio de Renda de Casa)
        sheet.set_column(17, 6, 30) # Column (Compensação Por Rescisão)
        sheet.set_column(18, 6, 30) # Column (Subsídio de Férias)
        sheet.set_column(19, 6, 30) # Column (Horas Extras)
        sheet.set_column(20, 6, 30) # Column (Subsídio de Atavio)
        sheet.set_column(21, 6, 30) # Column (Prémios)
        sheet.set_column(22, 6, 30) # Column (Subsídio de Natal)
        sheet.set_column(23, 6, 30) # Column (Outros Subsídios Sujeitos)
        sheet.set_column(24, 6, 30) # Column (Salário Ilíquido)
        sheet.set_column(25, 6, 30) # Column (Registo Manual de Contribuição Segurança Social?)
        sheet.set_column(26, 6, 30) # Column (Base Tributável Segurança Social)
        sheet.set_column(27, 6, 30) # Column (Base Tributável Segurança Social)
        sheet.set_column(28, 6, 45) # Column (Contribuição Segurança Social)
        sheet.set_column(29, 6, 45) # Column (Insento IRT?)
        sheet.set_column(30, 6, 45) # Column (IRT Apurado)

        # Write titles and header information
        # sheet.write(0, 0, 'NIF', title_format)
        # sheet.write(0, 1, model.company_id.vat, header_format)
        # sheet.write(1, 0, 'DATA FINAL', title_format)
        # sheet.write(1, 1, model.start_date.strftime('%Y-%m'), header_format)

        # Write column headers
        headers = [
            'ID',
            'NIF Trabalhador',
            'Nome',
            'Segurança Social',
            'Província',
            'Munícipio',
            'Salario Base',
            'Desconto por Falta',
            'Subsídio Alimentação',
            'Subsídio Transporte',
            'Abono Família',
            'Reembolso de Despesas',
            'Outros',
            'Calculo Manual de Excesso de Subsídios?',
            'Excesso Subsídios Não Sujeitos',
            'Abono de Falhas',
            'Subsídio de Renda de Casa',
            'Compensação Por Rescisão',
            'Subsídio de Férias',
            'Horas Extras',
            'Subsídio de Atavio',
            'Subsídio de Representação',
            'Prémios',
            'Subsídio de Natal',
            'Outros Subsídios Sujeitos',
            'Salário Ilíquido',
            'Registo Manual de Contribuição Segurança Social?',
            'Base Tributável Segurança Social',
            'Não Sujeito a Segurança Social?',
            'Contribuição Segurança Social',
            'Base Tributável IRT',
            'Insento IRT?',
            'IRT Apurado',
        ]
        for col_num, header in enumerate(headers):
            sheet.write(3, col_num, header, header_format)

        external_dados = data['data']

        row = 4
        col_num = 0
        control_list = 0

        while control_list < len(external_dados ):
            registries = list(external_dados [control_list].values())
            col_num = 0
            for value in registries:
                sheet.write(row, col_num, str(value), data_format)
                print(value)
                col_num += 1
            row += 1
            control_list += 1

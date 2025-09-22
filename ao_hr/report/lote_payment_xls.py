from odoo import models

class PaymentXlsx(models.AbstractModel):
    _name = 'report.ao_hr.lote.payment.xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, model):

        ############################
        # Criar a  planilha Início
        ###########################

        resumo_sheet = workbook.add_worksheet('Início')
        resumo_header_format = workbook.add_format({
            'font_size': 12,
            'align': 'center',
            'bold': True,
            'border': 1,
            'bg_color': '#013365',
            'font_color': '#FFFFFF'
        })
        resumo_data_format = workbook.add_format({'font_size': 10, 'align': 'center', 'border': 1})
        resumo_number_format = workbook.add_format(
            {'font_size': 10, 'align': 'center', 'border': 1, 'num_format': '#,##0.00'})

        #########################################
        # Define e escreve os Títulos do Cabeçalho
        ##########################################

        resumo_headers = ['Tipo Operação', 'NIB Conta a Debitar', 'Data Processamento', 'Referência do Ordenante']
        for col_num, header in enumerate(resumo_headers):
            resumo_sheet.write(0, col_num, header, resumo_header_format)
            resumo_sheet.set_column(col_num, col_num, 25)

        ############################################
        # Escrever os dados com a formatação correta
        ############################################

        dados_inicio = data.get('dados_inicio', {})
        resumo_sheet.write(1, 0, dados_inicio.get('operation_type', ''), resumo_data_format)
        resumo_sheet.write(1, 1, dados_inicio.get('account_debit_nib', ''), resumo_data_format)
        resumo_sheet.write(1, 2, dados_inicio.get('processing_date', ''), resumo_data_format)
        resumo_sheet.write(1, 3, dados_inicio.get('owner_reference', ''), resumo_data_format)

        ###################
        # Segunda folha
        ####################

        sheet1 = workbook.add_worksheet('Pagamento em Massa')

        ###################
        # Define os Formatos
        ####################

        title_format = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True})
        header_format = workbook.add_format({
            'font_size': 12,
            'align': 'center',
            'bold': True,
            'border': 1,
            'bg_color': '#013365',
            'font_color': '#FFFFFF'
        })
        data_format = workbook.add_format({'font_size': 10, 'align': 'center', 'border': 1})
        number_format = workbook.add_format({'font_size': 10, 'align': 'center', 'border': 1, 'num_format': '#,##0.00'})

        # Define o Cabeçalho por tipo
        if model.type == 'ps2':
            headers = [
                'IBAN',
                'Montante',
                'Nome',
                'Referência',
                'Email',
            ]
            sheet1.set_column(0, 0, 30)  # Increase height of the header row for type 'ps2' (30 pixels)
            sheet1.set_column(1, 1, 12)  # Increase height of the header row for type 'ps2' (30 pixels)
            sheet1.set_column(2, 2, 50)  # Increase height of the header row for type 'ps2' (30 pixels)
            sheet1.set_column(3, 3, 20)  # Increase height of the header row for type 'ps2' (30 pixels)
            sheet1.set_column(4, 4, 30)  # Increase height of the header row for type 'ps2' (30 pixels)

        else:
            headers = [
                'NIB',
                'Montante',
                'Tipo de Tranferencia',
                'Nome',
                'Morada',
                'BIC',
                'IBAN',
                'Motivo',
                'Categoria',
                'Detalhe',
                'Urgência',
            ]
            sheet1.set_column(0,0, 30)  # Increase height of the header row for other types (25 pixels)
            sheet1.set_column(1,1, 12)  # Increase height of the header row for other types (25 pixels)
            sheet1.set_column(2, 2,30)  # Increase height of the header row for other types (25 pixels)
            sheet1.set_column(3, 3,50)  # Increase height of the header row for other types (25 pixels)
            sheet1.set_column(4, 4, 70)  # Increase height of the header row for other types (25 pixels)
            sheet1.set_column(5, 5, 30)  # Increase height of the header row for other types (25 pixels)
            sheet1.set_column(6, 6, 30)  # Increase height of the header row for other types (25 pixels)
            sheet1.set_column(7, 7, 70)  # Increase height of the header row for other types (25 pixels)
            sheet1.set_column(8, 8, 80)  # Increase height of the header row for other types (25 pixels)
            sheet1.set_column(9, 9, 50)  # Increase height of the header row for other types (25 pixels)
            sheet1.set_column(10, 10, 100)  # Increase height of the header row for other types (25 pixels)

        ##################################
        # Escreve cabeçalhos de coluna
        ###################################

        for col_num, header in enumerate(headers):
            sheet1.write(0, col_num, header, header_format)

        external_dados = data['data']

        row = 1
        col_num = 0
        control_list = 0

        while control_list < len(external_dados):
            registries = list(external_dados[control_list].values())
            col_num = 0
            for value in registries:
                if isinstance(value, float):
                    sheet1.write(row, col_num, value, number_format)
                else:
                    sheet1.write(row, col_num, str(value), data_format)
                col_num += 1
            row += 1
            control_list += 1


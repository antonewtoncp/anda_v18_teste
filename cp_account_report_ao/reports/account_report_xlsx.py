from odoo import models
import xlwt
from datetime import datetime

class AccountExtractXls(models.AbstractModel):
    _name = 'report.es_account_report_ao.account.extract.xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def format_currency(self, value):
        """Formata números com vírgula como separador decimal"""
        if value == 0:
            return "0,00"
        try:
            # Formata com 2 casas decimais
            return "{:,.2f}".format(float(value)).replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "0,00"

    def format_date(self, date_str):
        """Formata data YYYY-MM-DD para DD/MM/YYYY"""
        if not date_str:
            return ""
        try:
            if isinstance(date_str, str):
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                return date_obj.strftime('%d/%m/%Y')
            elif hasattr(date_str, 'strftime'):
                return date_str.strftime('%d/%m/%Y')
        except:
            return str(date_str)
        return ""

    def generate_xlsx_report(self, workbook, data, model):
        wizard_data = data.get('form', {})
        wizard = self.env['account.extract.wizard'].browse(wizard_data.get('id'))
        
        # Obtém os movimentos usando o método do wizard
        all_movements = wizard.get_account_move_line()
            
        sheet = workbook.add_worksheet('Extracto de Conta')

        # Define formats
        title_format = workbook.add_format({
            'font_size': 16, 
            'align': 'left', 
            'bold': True,
            'font_color': '#0B74CE'
        })
        
        company_format = workbook.add_format({
            'font_size': 12,
            'align': 'left',
            'bold': True
        })
        
        address_format = workbook.add_format({
            'font_size': 10,
            'align': 'left'
        })
        
        header_format = workbook.add_format({
            'font_size': 10,
            'align': 'center',
            'bold': True,
            'border': 1,
            'bg_color': '#0B74CE',
            'font_color': '#FFFFFF',
            'text_wrap': True
        })
        
        data_format = workbook.add_format({
            'font_size': 9, 
            'align': 'left', 
            'border': 1,
            'text_wrap': False
        })
        
        number_format = workbook.add_format({
            'font_size': 9, 
            'align': 'right', 
            'border': 1
        })
        
        date_format = workbook.add_format({
            'font_size': 9,
            'align': 'left',
            'border': 1
        })
        
        account_header_format = workbook.add_format({
            'font_size': 11,
            'align': 'left',
            'bold': True,
            'bg_color': '#E6F3FF',
            'border': 1,
            'text_wrap': True
        })
        
        total_format = workbook.add_format({
            'font_size': 9,
            'align': 'right',
            'bold': True,
            'border': 1,
            'bg_color': '#F0F0F0'
        })
        
        initial_balance_format = workbook.add_format({
            'font_size': 9,
            'align': 'left',
            'bold': True,
            'border': 1,
            'bg_color': '#FAFAFA'
        })
        
        grand_total_format = workbook.add_format({
            'font_size': 10,
            'align': 'right',
            'bold': True,
            'border': 2,
            'bg_color': '#D4D4D4'
        })

        # Set column widths (mais precisos)
        sheet.set_column('A:A', 12)   # Data (12 caracteres)
        sheet.set_column('B:B', 35)   # Descrição (35 caracteres)
        sheet.set_column('C:C', 15)   # Débito (15 caracteres)
        sheet.set_column('D:D', 15)   # Crédito (15 caracteres)
        sheet.set_column('E:E', 15)   # Saldo (15 caracteres)

        # Company Info Header - MAIS ORGANIZADO
        row = 0
        sheet.write(row, 0, wizard.company_id.name.upper(), company_format)
        row += 1
        
        if wizard.company_id.street:
            sheet.write(row, 0, wizard.company_id.street, address_format)
            row += 1
        
        if wizard.company_id.city:
            city_country = wizard.company_id.city
            if wizard.company_id.country_id:
                city_country += f" - {wizard.company_id.country_id.name}"
            sheet.write(row, 0, city_country, address_format)
            row += 1
        
        row += 1  # Linha em branco

        # Report Title - CENTRALIZADO E CLARO
        report_title = "EXTRACTO DE CONTA"
        sheet.write(row, 0, report_title, title_format)
        row += 1
        
        # Subtítulo com informações das contas
        subtitle = ""
        if wizard.specific_account and wizard.account_ids:
            account_codes = ', '.join(wizard.account_ids.mapped('code'))
            subtitle = f"Contas: {account_codes}"
        elif wizard.account_from and wizard.account_to:
            subtitle = f"Intervalo: {wizard.account_from.code} a {wizard.account_to.code}"
        
        if subtitle:
            sheet.write(row, 0, subtitle, workbook.add_format({'bold': True}))
            row += 1
        
        # Período
        if wizard.date_from and wizard.date_to:
            period_text = f"Período: {wizard.date_from.strftime('%d/%m/%Y')} a {wizard.date_to.strftime('%d/%m/%Y')}"
            sheet.write(row, 0, period_text)
            row += 1
        
        # Info adicional em colunas separadas
        currency_info = workbook.add_format({'align': 'left'})
        emission_info = workbook.add_format({'align': 'right'})
        
        sheet.write(row, 0, f"Moeda: {wizard.company_id.currency_id.symbol}", currency_info)
        sheet.write(row, 4, f"Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", emission_info)
        row += 2

        # Write column headers - MAIS CLAROS
        headers = [
            'DATA', 
            'DESCRIÇÃO / DOCUMENTO', 
            'DÉBITO', 
            'CRÉDITO', 
            'SALDO'
        ]
        for col_num, header in enumerate(headers):
            sheet.write(row, col_num, header, header_format)
        row += 1

        if not all_movements:
            sheet.merge_range(row, 0, row, 4, 
                            "NENHUM MOVIMENTO ENCONTRADO PARA OS CRITÉRIOS SELECIONADOS", 
                            workbook.add_format({
                                'align': 'center', 
                                'bg_color': '#FFF3CD', 
                                'border': 1,
                                'italic': True
                            }))
            return

        # Variáveis para controle
        current_account = False
        account_total_debit = 0.0
        account_total_credit = 0.0
        grand_total_debit = 0.0
        grand_total_credit = 0.0

        for move_index, move in enumerate(all_movements):
            account_id = move.get('account_id')
            
            # Verifica se mudou de conta
            if current_account != account_id:
                # Fechar conta anterior se existir
                if current_account != False:
                    # Linha de total da conta
                    sheet.write(row, 1, "TOTAL DA CONTA", total_format)
                    sheet.write(row, 2, self.format_currency(account_total_debit), total_format)
                    sheet.write(row, 3, self.format_currency(account_total_credit), total_format)
                    sheet.write(row, 4, self.format_currency(account_total_debit - account_total_credit), total_format)
                    row += 1
                    row += 1  # Linha em branco para separação
                
                # Nova conta - Cabeçalho (mesclando todas as colunas)
                account_code = move.get('account_code', '')
                account_name = move.get('account_name', '')
                sheet.merge_range(row, 0, row, 4, 
                                f"{account_code} - {account_name}", 
                                account_header_format)
                row += 1
                
                # Saldo inicial (APENAS NA COLUNA DE SALDO)
                prev_balance = float(move.get('previous_balance', 0.0) or 0.0)
                sheet.write(row, 0, 
                          wizard.date_from.strftime('%d/%m/%Y') if wizard.date_from else '', 
                          initial_balance_format)
                sheet.write(row, 1, "SALDO INICIAL", initial_balance_format)
                sheet.write(row, 2, "", initial_balance_format)  # Débito vazio
                sheet.write(row, 3, "", initial_balance_format)  # Crédito vazio
                sheet.write(row, 4, self.format_currency(prev_balance), initial_balance_format)
                row += 1
                
                # Reinicializar variáveis da conta
                current_account = account_id
                account_total_debit = 0.0
                account_total_credit = 0.0

            # Linha do movimento - DADOS CORRETOS NAS COLUNAS CERTAS
            move_date = self.format_date(move.get('date', ''))
            description = str(move.get('description', '') or move.get('doc', '') or '').strip()
            debit = float(move.get('debit', 0.0) or 0.0)
            credit = float(move.get('credit', 0.0) or 0.0)
            balance = float(move.get('balance', 0.0) or 0.0)
            
            # Escreve nas colunas corretas
            sheet.write(row, 0, move_date, date_format)          # Coluna A: Data
            sheet.write(row, 1, description, data_format)        # Coluna B: Descrição
            sheet.write(row, 2, self.format_currency(debit), number_format)   # Coluna C: Débito
            sheet.write(row, 3, self.format_currency(credit), number_format)  # Coluna D: Crédito
            sheet.write(row, 4, self.format_currency(balance), number_format) # Coluna E: Saldo
            row += 1
            
            # Atualizar totais
            account_total_debit += debit
            account_total_credit += credit
            grand_total_debit += debit
            grand_total_credit += credit

        # Fechar última conta
        if current_account != False:
            sheet.write(row, 1, "TOTAL DA CONTA", total_format)
            sheet.write(row, 2, self.format_currency(account_total_debit), total_format)
            sheet.write(row, 3, self.format_currency(account_total_credit), total_format)
            sheet.write(row, 4, self.format_currency(account_total_debit - account_total_credit), total_format)
            row += 1

        # Linha em branco antes do total geral
        row += 1

        # Total Geral - CORRETAMENTE POSICIONADO
        grand_total_balance = grand_total_debit - grand_total_credit
        
        sheet.write(row, 1, "TOTAL GERAL", grand_total_format)
        sheet.write(row, 2, self.format_currency(grand_total_debit), grand_total_format)
        sheet.write(row, 3, self.format_currency(grand_total_credit), grand_total_format)
        sheet.write(row, 4, self.format_currency(grand_total_balance), grand_total_format)

        # Atualizar os totais no wizard
        wizard.write({
            'debit': grand_total_debit,
            'credit': grand_total_credit,
            'balance': grand_total_balance,
        })

        # Configurações finais
        sheet.set_default_row(18)  # Altura padrão das linhas
        sheet.freeze_panes(8, 0)   # Congela cabeçalhos

        # Adicionar bordas à área total do relatório
        last_col = 4  # Coluna E
        last_row = row
        sheet.conditional_format(0, 0, last_row, last_col, {
            'type': 'no_errors',
            'format': workbook.add_format({'border': 1})
        })
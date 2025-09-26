from datetime import datetime
from odoo import fields, models, api
from odoo.tools.misc import formatLang
import time
from dateutil.relativedelta import relativedelta
from pprint import pprint
from babel.numbers import format_decimal



class AccountExtractWizard(models.TransientModel):
    _name = 'account.extract.wizard'
    _description = 'Account Extract Wizard'

    #account_id = fields.Many2one('account.account', string="Account")

    account_ids = fields.Many2many(
    comodel_name='account.account', 
    relation='account_account_relation',  # Tabela relacional
    column1='current_model_id',        # Referência ao modelo atual
    column2='account_id',                  # Referência ao modelo 'treasury.box'
    string='Contas'
)
    
    account_from = fields.Many2one('account.account', string="From Account")
    account_to = fields.Many2one('account.account', string="To Account")
    date_from = fields.Date('Date From', default=time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date To', default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.company, string="Company")
    account_group_id = fields.Many2one(comodel_name='account.group', string='Group')
    filter_by = fields.Selection([('account', 'Account'), ('cost_center', 'Cost Center'),
                                  ('cash_flow', 'Cash Flow'), ('fiscal_plan', 'Fiscal Plan'), ('iva_plan', 'IVA Plan')],
                                 string='Filter By', default='account')
    display_account = fields.Selection([('all', 'All'), ('movement', 'Movement')], string='Display Account',
                                       default='movement')
    specific_account = fields.Boolean('Specifc Account?')
    cost_center = fields.Many2one(comodel_name="account.cost.center", string="Cost Center")
    cash_flow = fields.Many2one(comodel_name="account.cash.flow", string="Cash Flow")
    iva_plan = fields.Many2one(comodel_name="account.iva", string="Plan IVA")
    fiscal_plan = fields.Many2one(comodel_name="account.fiscal.plan", string="Plan Fiscal")
    by_account = fields.Boolean(string="By Account?")
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')
    debit = fields.Float(string="debit")
    credit = fields.Float(string="credit")
    balance = fields.Float(string="balance")

    @api.onchange('filter_by')
    def onchange_filter_by(self):
        self.by_account = False
        self.specific_account = False
        self.account_ids = False
        self.account_from = False
        self.account_to = False

    def account_setup(self, account_code):
        account = self.env['account.account'].search([('code', '=', account_code)])
        return {'account_id': account.id, 'account_code': account.code, 'account_name': account.name}

    def _args_query(self, account_ids=None):
        args = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            'move_id_states': tuple([self.target_move] if self.target_move == 'posted' else ['posted', 'draft'])
        }
        if account_ids:
            if isinstance(account_ids, (list, tuple)):
                args['account_ids'] = tuple(account_ids)
            else:
                args['account_id'] = account_ids
        return args

    def query_account_movements(self, account):
        """
        Consulta os movimentos de uma conta contábil específica.
        
        :param account: ID da conta ou objeto account
        :return: Lista de dicionários com os movimentos da conta
        """
        _query = """
            SELECT 
                line.id as line_id,
                line.date as date,
                journal.name as journal_name,
                journal.id as journal_id,
                SUM(line.debit) AS debit,
                SUM(line.credit) AS credit,
                SUM(line.debit - line.credit) AS balance,
                move.ref as description,
                move.name as doc,
                account.name as account_name
            FROM account_move_line line
            INNER JOIN account_account account ON line.account_id = account.id
            INNER JOIN account_journal journal ON line.journal_id = journal.id
            INNER JOIN account_move move ON line.move_id = move.id
            WHERE line.account_id = %(account_id)s
                AND line.date BETWEEN %(date_from)s AND %(date_to)s
                AND line.company_id = %(company_id)s
                AND move.state IN %(move_id_states)s
            GROUP BY 
                line.id, line.date, journal.name, journal.id, 
                move.ref, move.name, move.id,  account.name
            ORDER BY line.date, move.id
        """


        # Garante que temos um ID de conta
        account_id = account.id if hasattr(account, 'id') else account
        args = self._args_query(account_id)
        
        # Obtém o saldo anterior ao período
        previous_balance = self.get_previous_balance(account_id)
        
        # Executa a consulta
        self.env.cr.execute(_query, args)
        rows = self.env.cr.dictfetchall()
        
        # Inicializa variáveis para cálculo do saldo acumulado
        running_balance = previous_balance.get('balance', 0.0)
        
        # Processa cada linha para adicionar o saldo acumulado
        for row in rows:
            # Calcula o saldo acumulado
            running_balance += (row.get('debit', 0.0) - row.get('credit', 0.0))
            
            # Adiciona informações adicionais à linha
            row.update({
                'current_balance': running_balance,
                'balance_type': 'D' if running_balance >= 0 else 'C',
                'previous_balance': previous_balance.get('balance', 0.0),
                'previous_debit': previous_balance.get('debit', 0.0),
                'previous_credit': previous_balance.get('credit', 0.0),
            })
            
            # Se for a primeira linha, adiciona o saldo anterior
            if row == rows[0]:
                row['is_first'] = True
            
        return rows

    def query_cost_center_movements(self, cost_center, account_id):
        _query = """
                      SELECT account.name As account_name, account.code As account_code, line.date, journal.name As journal_name, journal.id As journal, SUM(line.debit) AS debit, SUM(line.credit) AS credit, SUM(line.balance) AS balance, move.ref as description, move.name As doc
                      FROM account_move_line line
                       INNER JOIN account_account account ON
                           line.account_id = account.id
                       INNER JOIN account_journal journal ON
                           line.journal_id = journal.id 
                       INNER JOIN account_move move ON
                           line.move_id = move.id
                      WHERE (line.account_id = %(account_id)s)
                          AND (line.cost_Center = %(cost_center)s)
                          AND (line.date >= %(date_from)s)
                          AND (line.date <= %(date_to)s)
                          AND (line.company_id = %(company_id)s)
                          AND (line.move_id_state IN %(move_id_states)s)
                      GROUP BY account.code, account.name, line.date, journal.name, journal.id, move.name, move.ref          
              """

        data = []
        balance = 0.0
        balance_debit = 0.0
        balance_credit = 0.0
        current_balance = 0.0
        args = self._args_query()
        args['account_id'] = account_id
        args['cost_center'] = cost_center
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            balance = row['balance']
            row['balance_debit'] = 0.0  # start
            row['balance_credit'] = 0.0  # start

            if row['credit'] > row['debit']:
                current_balance -= balance
                balance_credit += row['credit']
                row['current_balance'] = current_balance
                row['balance_credit'] = balance_credit
                row['balance_type'] = 'C'

            elif row['debit'] > row['credit']:
                current_balance += balance
                balance_debit += row['debit']
                row['current_balance'] = current_balance
                row['balance_debit'] = balance_debit
                row['balance_type'] = 'D'

            else:
                row['current_balance'] = 0.0
                row['balance_debit'] = 0.0
                row['balance_type'] = ''

            balance = row['balance']
            data.append(row)
        return data
        pass

    def _query_cost_center_account_ids(self, cost_center):
        _query = """
                   SELECT account.code As account_id
                   FROM account_move_line line
                     INNER JOIN account_account account ON
                           line.account_id = account.id
                   WHERE ((%(cost_center)s IS NULL AND line.cost_center IS NULL)
                        OR (%(cost_center)s IS NOT NULL))
                       AND (line.date >= %(date_from)s)
                       AND (line.date <= %(date_to)s)
                       AND (line.company_id = %(company_id)s)
                       AND (line.move_id_state IN %(move_id_states)s)
                   GROUP BY account.code
               """

        data = []
        args = self._args_query()
        args['cost_center'] = cost_center.id
        self.env.cr.execute(_query, args)
        for row in self.env.cr.fetchall():
            data.extend(list(set(row)))
        print(data)
        return data

    def query_fiscal_movements(self, fiscal_plan):
        _query = """
                        SELECT account.name As account_name, account.code As account_code, line.date, journal.name As journal_name, journal.id As journal, SUM(line.debit) AS debit, SUM(line.credit) AS credit, SUM(line.balance) AS balance, move.ref as description, move.name As doc
                        FROM account_move_line line
                         INNER JOIN account_account account ON
                             line.account_id = account.id
                         INNER JOIN account_journal journal ON
                             line.journal_id = journal.id 
                         INNER JOIN account_move move ON
                             line.move_id = move.id
                        WHERE ((%(fiscal_plan)s IS NULL AND line.fiscal_plan IS NULL)
                        OR (%(fiscal_plan)s IS NOT NULL))
                            AND (line.date >= %(date_from)s)
                            AND (line.date <= %(date_to)s)
                            AND (line.company_id = %(company_id)s)
                            AND (line.move_id_state IN %(move_id_states)s)
                        GROUP BY account.name, account.code, line.date, journal.name, journal.id, move.name, move.ref
                    """
        args = self._args_query()
        args['fiscal_plan'] = fiscal_plan.id
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            print(row)
            
    def get_previous_december_balance(self):
        year = fields.Date.from_string(self.date_from).year-1
        date_from = fields.Date.to_string(datetime(year, 12, 1))
        date_to = fields.Date.to_string(datetime(year, 12, 31))

        if not self.account_id:
            return {
            'debit': 0.0,
            'credit': 0.0,
            'balance': 0.0,
        }
    
        query = """
            SELECT
                SUM(debit) AS debit,
                SUM(credit) AS credit,
                SUM(balance) AS balance
            FROM account_move_line
            WHERE account_id = %s
                AND date BETWEEN %s AND %s
                AND company_id = %s
                AND move_id IN (
                    SELECT id FROM account_move
                    WHERE state IN %s
                )
            """
        states = tuple([self.target_move] if self.target_move == 'posted' else ['posted', 'draft'])

        self.env.cr.execute(query, (
            self.account_id.id,
            date_from,
            date_to,
            self.company_id.id,
            states
        ))

        row = self.env.cr.dictfetchone()
        return {
            'debit': row.get('debit') or 0.0,
            'credit': row.get('credit') or 0.0,
            'balance': row.get('balance') or 0.0,
        }

    def query_cash_flow_movements(self, cash_flow):
        pass

    def query_iva_movements(self, iva_plan):
        pass

    def get_account_move_line(self, account=None):
        """
        Retorna as linhas de movimento para uma conta específica ou para múltiplas contas.
        
        :param account: ID da conta ou objeto account (opcional)
        :return: Lista de dicionários com os movimentos da(s) conta(s)
        """
        def format_movement(account_id, account_code, account_name, move, previous_balance=None):
            """Formata os dados do movimento para o template."""
            movement = {
                'account_id': account_id,
                'account_code': account_code,
                'account_name': account_name,
                'date': move.get('date', ''),
                'journal_name': move.get('journal_name', ''),
                'journal': move.get('journal', ''),
                'description': move.get('description', ''),
                'debit': move.get('debit', 0.0),
                'credit': move.get('credit', 0.0),
                'balance': move.get('current_balance', 0.0),
                'doc': move.get('doc', ''),
                'balance_type': move.get('balance_type', ''),
            }
            
            # Adiciona saldo anterior se fornecido
            if previous_balance:
                movement.update({
                    'previous_debit': previous_balance.get('debit', 0.0),
                    'previous_credit': previous_balance.get('credit', 0.0),
                    'previous_balance': previous_balance.get('balance', 0.0),
                })
            else:
                movement.update({
                    'previous_debit': 0.0,
                    'previous_credit': 0.0,
                    'previous_balance': 0.0,
                })
                
            return movement
        
        all_movements = []
        
        # Se uma conta específica for fornecida, retorna apenas os movimentos dela
        if account:
            if isinstance(account, int):
                account = self.env['account.account'].browse(account)
            
            # Obtém o saldo anterior
            previous_balance = self.get_previous_balance(account.id)
            
            # Obtém os movimentos da conta
            movements = self.query_account_movements(account.id)
            
            # Formata os movimentos (sempre com previous_* preenchido por conta)
            for move in movements:
                all_movements.append(format_movement(
                    account.id,
                    account.code,
                    account.name,
                    move,
                    previous_balance
                ))
            
            return all_movements
        
        # Se houver contas específicas selecionadas
        if self.specific_account and self.account_ids:
            for acc in self.account_ids:
                # Obtém o saldo anterior
                previous_balance = self.get_previous_balance(acc.id)
                
                # Obtém os movimentos da conta
                movements = self.query_account_movements(acc.id)
                
                # Formata os movimentos (sempre com previous_* preenchido por conta)
                for move in movements:
                    all_movements.append(format_movement(
                        acc.id,
                        acc.code,
                        acc.name,
                        move,
                        previous_balance
                    ))
        # Se houver um intervalo de contas definido
        elif self.account_from and self.account_to and not self.specific_account:
            accounts = self.env['account.account'].search([
                ('code', '>=', self.account_from.code),
                ('code', '<=', self.account_to.code),
                ('company_ids', 'in', [self.company_id.id])
            ])
            
            for acc in accounts:
                # Obtém o saldo anterior
                previous_balance = self.get_previous_balance(acc.id)
                
                # Obtém os movimentos da conta
                movements = self.query_account_movements(acc.id)
                
                # Formata os movimentos (sempre com previous_* preenchido por conta)
                for move in movements:
                    all_movements.append(format_movement(
                        acc.id,
                        acc.code,
                        acc.name,
                        move,
                        previous_balance
                    ))
        
        # Ordena por conta e data
        all_movements.sort(key=lambda x: (x['account_code'], x['date']))
        
        return all_movements

    def get_cost_center_move_line(self, cost_center=None, account=None):
        return self.query_cost_center_movements(cost_center, account)

    def get_other_move_line(self):
        if self.filter_by == 'cost_center':
            if not self.by_account:
                for cost_center in self.env['account.cost.center'].search([]):
                    pass
            return self._query_cost_center_account_ids(self.cost_center)
        elif self.filter_by == 'fiscal_plan':
            self.query_fiscal_movements(self.fiscal_plan)

    def amount_format(self, value):
        return format_decimal(value, locale='pt_PT')

    def print_report(self):
        """
        Gera o relatório de extrato de contas.
        
        :return: Ação para gerar o relatório PDF
        """
        self.ensure_one()
        
        # Inicializa totais
        total_debit = 0.0
        total_credit = 0.0
        total_balance = 0.0
        
        # Lista de IDs de contas para processar
        account_ids = []
        
        # Se houver contas específicas selecionadas
        if self.specific_account and self.account_ids:
            account_ids = self.account_ids.ids
        # Se houver um intervalo de contas
        elif self.account_from and self.account_to and not self.specific_account:
            accounts = self.env['account.account'].search([
                ('code', '>=', self.account_from.code),
                ('code', '<=', self.account_to.code),
                ('company_ids', 'in', [self.company_id.id])
            ])
            account_ids = accounts.ids
        
        # Calcula os totais para cada conta
        for account_id in account_ids:
            # Obtém o saldo anterior para a conta
            balance = self.get_previous_balance(account_id)
            
            # Obtém os movimentos da conta para calcular os totais do período
            movements = self.query_account_movements(account_id)
            
            # Calcula os totais do período
            period_debit = sum(move.get('debit', 0.0) for move in movements)
            period_credit = sum(move.get('credit', 0.0) for move in movements)
            
            # Atualiza os totais gerais
            total_debit += balance.get('debit', 0.0) + period_debit
            total_credit += balance.get('credit', 0.0) + period_credit
            total_balance += balance.get('balance', 0.0) + (period_debit - period_credit)
        
        # Atualiza os campos no wizard
        self.write({
            'debit': total_debit,
            'credit': total_credit,
            'balance': total_balance,
        })
        
        # Retorna a ação para gerar o relatório
        return self.env.ref('cp_account_report_ao.action_report_account_extract_ao').report_action(self)
    
    def print_xls_report(self):
        # Gera os dados de acordo com a seleção do wizard (contas específicas ou intervalo)
        dados = self.get_account_move_line()
        return self.env.ref('cp_account_report_ao.action_report_account_extract_xlsx').report_action(
            self,
            data={'data': dados, 'form': self.read()[0]},
        )

    def get_previous_balance(self, account_id):
        """
        Retorna o saldo da conta desde o início até o dia anterior a date_from.
        
        :param account_id: ID da conta
        :return: Dicionário com os valores de débito, crédito e saldo
        """
        if not account_id or not self.date_from:
            return {
                'debit': 0.0,
                'credit': 0.0,
                'balance': 0.0,
            }

        # Calcula a data final (dia anterior ao início do período)
        date_to = fields.Date.from_string(self.date_from) - relativedelta(days=1)

        # Define os estados dos lançamentos a serem considerados
        states = ['posted']
        if self.target_move == 'all':
            states.append('draft')

        # Consulta para obter o saldo anterior (até o dia anterior ao período)
        query = """
            SELECT
                COALESCE(SUM(line.debit), 0.0) AS debit,
                COALESCE(SUM(line.credit), 0.0) AS credit,
                COALESCE(SUM(line.debit - line.credit), 0.0) AS balance
            FROM account_move_line line
            INNER JOIN account_move move ON line.move_id = move.id
            WHERE line.account_id = %s
                AND line.date <= %s
                AND line.company_id = %s
                AND move.state IN %s
        """

        self.env.cr.execute(query, (
            account_id,
            fields.Date.to_string(date_to),
            self.company_id.id,
            tuple(states)
        ))

        row = self.env.cr.dictfetchone()
        
        return {
            'debit': row.get('debit', 0.0),
            'credit': row.get('credit', 0.0),
            'balance': row.get('balance', 0.0),
        }
from odoo import fields, models, api, _
from odoo.tools.misc import formatLang
from datetime import datetime
import calendar


class AccountReportTrialBalance(models.TransientModel):
    _name = "account.report.trial.balance"
    _description = "Trial Balance Angola"
    _rec_name = "fiscal_year"

    fiscal_year = fields.Many2one(
        comodel_name="account.fiscal.year", string="Fiscal Year"
    )
    periods = fields.Many2many(comodel_name="account.fiscal.period", string="Period")
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda l: l.env.user.company_id,
        string="Company",
    )
    target_move = fields.Selection(
        [("posted", "Posted Entries only"), ("all", "All Entries")],
        string="Accounting Movements",
        default="posted",
    )
    type = fields.Selection(
        [("general", "General"), ("reason", "Reason")], default="general", string="Type"
    )

    opened = fields.Boolean(string="Abertura Automática", default=True)



    def get_open_period(self):
        if self.date_from:
            year = self.date_from.year
            date_from_fixed = datetime(year, 1, 1).date()

            open_period = self.env['account.fiscal.period'].search([
                ('start_date', '=', date_from_fixed),
                ('period', '=', 0),
                ('company_id', '=', self.company_id.id)
            ])
            return open_period
        # Apuramento = 14, Fecho = 15, Abertura = 0, Regularização = 13, Entradas = 12, Saida = 11
    def get_all_period(self):
        all_period = []
        year = self.date_from.year
        date_from_fixed = datetime(year, 1, 1).date()
        open_period = self.env['account.fiscal.period'].search([
            ('start_date', '=', date_from_fixed),
            ('period', 'in', [0, 12, 13, 14, 15]),
            ('company_id', '=', self.company_id.id)
        ])
        for period in open_period:
            all_period.append(period.id)
        return all_period


    # def get_previous_date(self, data_str, end_date):
    #     actual_date_from = data_str
    #     actual_date_to = end_date
    #     min_date = actual_date_from.replace(year=actual_date_to.year - 1)
    #     previous_date_from = min_date
    #     previous_date_to = actual_date_to.replace(year=actual_date_to.year - 1)        
    #     return previous_date_from, previous_date_to

    def get_previous_date(self, data_str, end_date):
        actual_date_from = data_str
        actual_date_to = end_date

        year_from = actual_date_to.year - 2
        last_day_from = calendar.monthrange(year_from, actual_date_from.month)[1]
        min_date = actual_date_from.replace(year=year_from, day=min(actual_date_from.day, last_day_from))

        year_to = actual_date_to.year - 2
        last_day_to = calendar.monthrange(year_to, actual_date_to.month)[1]
        previous_date_to = actual_date_to.replace(year=year_to, day=min(actual_date_to.day, last_day_to))

        return min_date, previous_date_to


    def _args_query_befor(self):
        previous_date_from, previous_date_to = self.get_previous_date(self.date_from, self.date_to)
        return {
            'date_from': previous_date_from,
            'date_to': self.date_to,
            'init_year': self.date_from,
            'company_id': self.company_id.id,
            'periods': tuple(self.periods.ids),
            'move_id_states': tuple([self.target_move] if self.target_move == 'posted' else ['posted', 'draft']),
            'all_period': tuple(self.get_all_period()),
            'filtered_reason_codes': tuple(['11', '12', '13', '14', '18', '21', '26', '31', '32', '33', '34', '35', '36', '37', '38', '39', '41', '42', '43', '45', '47', '48', '51', '55', '81']),
            'filtered_integrator_codes': ['11%', '12%', '13%', '14%', '181%', '21%', '26%', '31%', '32%', '33%', '34%', '35%', '36%', '37%', '38%', '39%', '41%', '42%', '43%', '45%', '47%', '48%', '51%', '55%', '81%']
        }


    @api.onchange('fiscal_year')
    def onchange_fiscal_year(self):
        self.date_from = self.fiscal_year.date_from
        self.date_to = self.fiscal_year.date_to
        self.periods = False

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.date_from = False
        self.date_to = False
        self.fiscal_year = False
        self.periods = False

    def _args_query(self):
        return {
            'init_year': self.date_from,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            'periods': tuple(self.periods.ids),
            'all_period': tuple(self.get_all_period()),
            'move_id_states': tuple([self.target_move] if self.target_move == 'posted' else ['posted', 'draft'])
        }

    def get_balance_reason(self):
        reason_balance = []
        reason_group = self.env['account.account'].search([('nature', '=', 'R'), ('company_ids', 'in', self.company_id.id)])
        for reason in reason_group:
            _before_codes = []
            record = self.query_reason_balance(reason.code)
            if record is not None:
                record['name'] = reason.name.upper()
                record['nature'] = reason.nature
                balance = record['balance']
                record['balance_debit'] = balance if balance > 0.0 else 0.0
                record['balance_credit'] = balance * -1 if balance < 0.0 else 0.0
                reason_balance.append(record)
        return reason_balance

    def get_balance_general(self):
        general_balance = []
        reason_group = self.env['account.account'].search([('nature', '=', 'R'), ('company_ids', 'in', self.company_id.id)])
        integrator_group = self.env['account.account'].search([('nature', '=', 'I'), ('company_ids', 'in', self.company_id.id)])
        for reason in reason_group:
            _before_codes = []
            record = self.query_reason_balance(reason.code)
            if record is not None:
                record['name'] = reason.name.upper()
                record['nature'] = reason.nature
                balance = record['balance']
                record['balance_debit'] = balance if balance > 0.0 else 0.0
                record['balance_credit'] = balance * -1 if balance < 0.0 else 0.0
                general_balance.append(record)
            for integrator in integrator_group:
                if integrator.reason_code == reason.code:

                    # NORMAL CASE
                    record = self.query_integrator_balance(integrator.code)
                    if record:
                        record['name'] = integrator.name
                        record['nature'] = integrator.nature
                        balance = record['balance']
                        record['balance_debit'] = balance if balance > 0.0 else 0.0
                        record['balance_credit'] = balance * -1 if balance < 0.0 else 0.0
                        general_balance.append(record)

                        accounts = self._get_movement_nature_accounts(integrator.code)
                        for account in accounts:
                            record = self.query_account_move(account.code)
                            if record is not None:
                                record['name'] = account.name
                                record['nature'] = account.nature
                                balance = record['balance']
                                record['balance_debit'] = balance if balance > 0.0 else 0.0
                                record['balance_credit'] = balance * -1 if balance < 0.0 else 0.0
                                general_balance.append(record)
                    else:
                        # _before_codes.append(integrator.code)
                        _count = 0
                        _sum_balance = 0.0
                        accounts = self._get_parent_integrator(integrator.code)
                        _record = {'code': '', 'debit': 0, 'credit': 0, 'balance_debit': 0, 'balance_credit': 0, }
                        for account in accounts:
                            record = self.query_integrator_balance(account.code)
                            if record is not None:
                                balance = record['balance']
                                _record['debit'] += record['debit']
                                _record['credit'] += record['credit']
                                _record['balance_debit'] += balance if balance > 0.0 else 0.0
                                _record['balance_credit'] += balance * -1 if balance < 0.0 else 0.0
                                _record['code'] = integrator.code
                                _record['name'] = integrator.name
                                _record['nature'] = integrator.nature
                                _count += 1
                                _sum_balance += balance

                        if _count > 0: general_balance.append(_record)

        for data_integrator in self.trial_balance(general_balance):
            for general in general_balance:
                if data_integrator['code'] == general['code']:
                    general['debit'] = data_integrator['debit']
                    general['credit'] = data_integrator['credit']
                    general['balance'] = data_integrator['balance']
                    general['balance_debit'] = data_integrator['balance_debit']
                    general['balance_credit'] = data_integrator['balance_credit']
        return general_balance

    def query_reason_balance(self, code):
        args = self._args_query_befor()
        if not self.opened:
            _query = """
                SELECT reason_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                FROM account_move_line 
                WHERE (reason_code = %(reason_code)s)
                    AND (date >= %(init_year)s)
                    AND (date <= %(date_to)s)
                    AND (company_id = %(company_id)s)
                    AND (move_id_state IN %(move_id_states)s)
                    AND (period IN %(periods)s OR period NOT IN %(all_period)s)
                GROUP BY reason_code
            """
        elif len(self.periods.ids) == 1 and self.periods.ids[0] == self.get_open_period().id:
            _query = """
                SELECT reason_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                FROM account_move_line 
                WHERE (reason_code = %(reason_code)s)
                    AND (date >= %(date_from)s)
                    AND (date <= %(init_year)s)
                    AND (company_id = %(company_id)s)
                    AND (move_id_state IN %(move_id_states)s)
                    AND (reason_code IN %(filtered_reason_codes)s)
                GROUP BY reason_code
            """
        elif self.get_open_period().id not in self.periods.ids:
            _query = """
                SELECT reason_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                FROM account_move_line 
                WHERE (reason_code = %(reason_code)s)
                    AND (date >= %(date_from)s)
                    AND (date <= %(date_to)s)
                    AND (company_id = %(company_id)s)
                    AND (move_id_state IN %(move_id_states)s)
                    AND (period IN %(periods)s OR period NOT IN %(all_period)s)
                GROUP BY reason_code
            """
            args = self._args_query()
        else:
            if len(self.periods.ids) == 5:
                _query = """
                    SELECT reason_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                    FROM account_move_line 
                        WHERE (reason_code = %(reason_code)s)
                        AND ((date >= %(init_year)s) OR (date >= %(date_from)s AND date < %(init_year)s AND reason_code IN %(filtered_reason_codes)s))
                        AND (date <= %(date_to)s)
                        AND (company_id = %(company_id)s)
                        AND (move_id_state IN %(move_id_states)s)
                    GROUP BY reason_code
                """
            else:
                _query = """
                    SELECT reason_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                    FROM account_move_line 
                        WHERE (reason_code = %(reason_code)s)
                        AND ((date >= %(init_year)s AND (period IN %(periods)s OR period NOT IN %(all_period)s)) OR (date >= %(date_from)s AND date < %(init_year)s AND reason_code IN %(filtered_reason_codes)s))
                        AND (date <= %(date_to)s)
                        AND (company_id = %(company_id)s)
                        AND (move_id_state IN %(move_id_states)s)
                    GROUP BY reason_code
                """

        args['reason_code'] = code
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            return row
        return None

    def query_integrator_balance(self, code):
        args = self._args_query_befor()
        if not self.opened:
            _query = """
                SELECT integrator_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                FROM account_move_line 
                WHERE (integrator_code = %(integrator_code)s)
                    AND (date >= %(init_year)s)
                    AND (date <= %(date_to)s)
                    AND (company_id = %(company_id)s)
                    AND (move_id_state IN %(move_id_states)s)
                    AND (period IN %(periods)s OR period NOT IN %(all_period)s)
                GROUP BY integrator_code
            """
        elif len(self.periods.ids) == 1 and self.periods.ids[0] == self.get_open_period().id:
            _query = """
                SELECT integrator_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                FROM account_move_line 
                    WHERE (integrator_code = %(integrator_code)s)
                    AND (date >= %(date_from)s)
                    AND (date < %(init_year)s)
                    AND (company_id = %(company_id)s)
                    AND (move_id_state IN %(move_id_states)s)
                    AND (
                        (date < %(init_year)s AND integrator_code LIKE ANY(%(filtered_integrator_codes)s))
                    ) 
                GROUP BY integrator_code
            """
        elif self.get_open_period().id not in self.periods.ids:
            _query = """
                SELECT integrator_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                FROM account_move_line 
                WHERE (integrator_code = %(integrator_code)s)
                    AND (date >= %(date_from)s)
                    AND (date <= %(date_to)s)
                    AND (company_id = %(company_id)s)
                    AND (move_id_state IN %(move_id_states)s)
                    AND (period IN %(periods)s OR period NOT IN %(all_period)s)
                GROUP BY integrator_code
            """
            args = self._args_query()
        else:
            if len(self.periods.ids) == 5:
                _query = """
                    SELECT integrator_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                    FROM account_move_line 
                        WHERE (integrator_code = %(integrator_code)s)
                        AND ((date >= %(init_year)s) OR (date >= %(date_from)s AND date < %(init_year)s AND integrator_code LIKE ANY(%(filtered_integrator_codes)s)))
                        AND (date <= %(date_to)s)
                        AND (company_id = %(company_id)s)
                        AND (move_id_state IN %(move_id_states)s)
                    GROUP BY integrator_code
                """
            else:
                _query = """
                    SELECT integrator_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                    FROM account_move_line 
                        WHERE (integrator_code = %(integrator_code)s)
                        AND ((date >= %(init_year)s AND (period IN %(periods)s OR period NOT IN %(all_period)s)) OR (date >= %(date_from)s AND date < %(init_year)s AND integrator_code LIKE ANY(%(filtered_integrator_codes)s)))
                        AND (date <= %(date_to)s)
                        AND (company_id = %(company_id)s)
                        AND (move_id_state IN %(move_id_states)s)
                    GROUP BY integrator_code
                """
        args['integrator_code'] = code
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            return row
        return None

    def query_account_move(self, code):
        args = self._args_query_befor()
        if not self.opened:
            _query = """
                SELECT account_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                FROM account_move_line 
                WHERE (account_code = %(account_code)s)
                    AND (date >= %(init_year)s)
                    AND (date <= %(date_to)s)
                    AND (company_id = %(company_id)s)
                    AND (move_id_state IN %(move_id_states)s)
                    AND (period IN %(periods)s OR period NOT IN %(all_period)s)
                GROUP BY account_code
            """
        elif len(self.periods.ids) == 1 and self.periods.ids[0] == self.get_open_period().id:
            _query = """
                SELECT account_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                FROM account_move_line 
                    WHERE (account_code = %(account_code)s)
                    AND (date >= %(date_from)s)
                    AND (date < %(init_year)s)
                    AND (company_id = %(company_id)s)
                    AND (move_id_state IN %(move_id_states)s)
                    AND (
                        (date < %(init_year)s AND account_code LIKE ANY(%(filtered_integrator_codes)s))
                    )  
                GROUP BY account_code
            """
        elif self.get_open_period().id not in self.periods.ids:
            _query = """
                SELECT account_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                FROM account_move_line 
                WHERE (account_code = %(account_code)s)
                    AND (date >= %(date_from)s)
                    AND (date <= %(date_to)s)
                    AND (company_id = %(company_id)s)
                    AND (move_id_state IN %(move_id_states)s)
                    AND (period IN %(periods)s OR period NOT IN %(all_period)s)
                GROUP BY account_code
            """
            args = self._args_query()
        else:
            if len(self.periods.ids) == 5:
                _query = """
                    SELECT account_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                    FROM account_move_line 
                        WHERE (account_code = %(account_code)s)
                        AND ((date >= %(init_year)s) OR (date >= %(date_from)s AND date < %(init_year)s AND account_code LIKE ANY(%(filtered_integrator_codes)s)))
                        AND (date <= %(date_to)s)
                        AND (company_id = %(company_id)s)
                        AND (move_id_state IN %(move_id_states)s)
                    GROUP BY account_code
                """
            else:
                _query = """
                    SELECT account_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
                    FROM account_move_line 
                        WHERE (account_code = %(account_code)s)
                        AND ((date >= %(init_year)s AND (period IN %(periods)s OR period NOT IN %(all_period)s)) OR (date >= %(date_from)s AND date < %(init_year)s AND account_code LIKE ANY(%(filtered_integrator_codes)s)))
                        AND (date <= %(date_to)s)
                        AND (company_id = %(company_id)s)
                        AND (move_id_state IN %(move_id_states)s)
                    GROUP BY account_code
                """
        
        args['account_code'] = code
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            return row
        return None

    def _get_movement_nature_accounts(self, integrator_code):
        accounts = self.env["account.account"].search(
            [("nature", "=", "M"), ("integrator_code", "=", integrator_code), ('company_ids', 'in', self.company_id.id)]
        )
        # self.env.user.has_group('base.group_system')
        return accounts

    def _get_parent_integrator(self, code):
        accounts = self.env["account.account"].search(
            [("nature", "=", "I"), ("integrator_code", "=", code), ('company_ids', 'in', self.company_id.id)]
        )
        return accounts

    def trial_balance(self, general_balance):
        reason_group = self.env["account.account"].search([("nature", "=", "R"), ('company_ids', 'in', self.company_id.id)])
        integrator_data = []
        _except = []
        debit = credit = balance = balance_debit = balance_credit = 0.0
        for prefix in reason_group:
            for suffix in range(1, 10):
                for data in general_balance:
                    if prefix.code + str(suffix) == data["code"]:
                        _except.append(prefix.code + str(suffix))
                        continue
                    if (
                            prefix.code + str(suffix)
                            in data["code"][: len(prefix.code + str(suffix))]
                            and data["nature"] == "M"
                    ):
                        debit += data["debit"]
                        credit += data["credit"]
                        balance += data.get("balance") or 0.0
                        balance_debit += data["balance_debit"]
                        balance_credit += data["balance_credit"]
                if not _except:
                    integrator_data.append(
                        {
                            "code": prefix.code + str(suffix),
                            "debit": debit,
                            "credit": credit,
                            "balance": balance,
                            "balance_debit": balance_debit,
                            "balance_credit": balance_credit,
                        }
                    )
                _except = []
                debit = credit = balance = balance_debit = balance_credit = 0.0
        return integrator_data

    def check_balance_integrator_account(self, code):
        account = self.env["account.account"].search([("code", "=", code), ('company_ids', 'in', self.company_id.id)], limit=1)
        if account.current_balance != 0:
            return True
        return False

    def _get_periods(self, code):
        accounts = self.env["account.fiscal.period"].search(
            [("nature", "=", "I"), ("integrator_code", "=", code), ('company_id', '=', self.company_id.id)]
        )
        return accounts

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    def name_balance(self):
        name = set()
        d2 = self.date_from.strftime("%B")
        d3 = self.date_to.strftime("%B")

        for rec in self:
            for re in rec.periods:
                name.add(re.period)
        if (
                "0" in name
                and "12" not in name
                and "13" not in name
                and "14" not in name
                and "15" not in name
        ):
            return f'{d2, " / ", d3}'.replace(",", "")
        if (
                "12" in name
                and "13" in name
                and "0" not in name
                and "15" not in name
                and "14" not in name
        ):
            return f'{d2, " / ", "Reg"}'.replace(",", "")
        if (
                "12" in name
                and "13" in name
                and "14" in name
                and "0" not in name
                and "15" not in name
        ):
            return f'{d2, "/", "Fim"}'.replace(",", "")
        if (
                "12" in name
                and "13" in name
                and "0" in name
                and "14" not in name
                and "15" not in name
        ):
            return "Abertura / Regularização"
        if (
                "0" in name
                and "12" in name
                and "13" in name
                and "14" in name
                and "15" in name
        ):
            return "Abertura / Fim"
        else:
            if re.period == "12":
                return "Entradas Comuns"
            if re.period == "13":
                return "Entradas de Regularização"
            if re.period == "14":
                return "Liberação"
            if re.period == "15":
                return "Fechamento"

    def print_pdf(self):
        for record in self:
            if record.opened:
                if len(record.periods) == 1 and record.periods.name == "Abertura":
                    return self.env.ref('cp_account_report_ao.action_report_trial_open_balance_ao').report_action(self)
                else:
                    return self.env.ref('cp_account_report_ao.action_report_trial_balance_ao').report_action(self)
            else:
                if len(record.periods) == 1 and record.periods.name == "Abertura":
                    return self.env.ref('cp_account_report_ao.action_report_trial_open_balance_ao').report_action(self)
                else:
                    return self.env.ref('cp_account_report_ao.action_report_trial_old_balance_ao').report_action(self)
                
    # def print_pdf(self):
    #     return self.env.ref(
    #         "cp_account_report_ao.action_report_trial_balance_ao"
    #     ).report_action(self)

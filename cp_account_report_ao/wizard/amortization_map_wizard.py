from datetime import datetime
from odoo import fields, models, api
from odoo.tools.misc import formatLang
import time
from dateutil.relativedelta import relativedelta


class Amortization(models.Model):
    _inherit = "account.asset"

    open_date = fields.Date("Open Date", default=time.strftime("2022-01-31"))
    date_out = fields.Date(
        "Out Date",
        default=lambda self: fields.Date.to_string(
            (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        ),
    )
    is_import = fields.Boolean("Is import?", help="Se o produto foi importado ou não")
    number = fields.Integer("Utility Number")
    acquisition = fields.Boolean("Acquisition")
    tax = fields.Float("Tax", default=25)
    tax_corrected = fields.Float("Tax Corrected", default=25)


class Amortization(models.TransientModel):
    _name = "amortization.map.wizard"
    _description = "Amortization Map"

    date_from = fields.Date("Date From", default=time.strftime("2018-01-01"))
    date_to = fields.Date(
        default=lambda self: fields.Date.to_string(
            (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        )
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda l: l.env.user.company_id,
        string="Company",
    )
    accounting_year = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Ano Fiscal",
        default=lambda self: self.env.user.company_id.accounting_year,
    )

    nature_assets = fields.Selection(
        [
            ("tangible", "Activos Fixos Tangíveis"),
            ("Intangibles", "Activos Fixos Intangívei"),
            ("biological", "Activos Biológicos Não"),
            ("investment", "Propriedade de Investimento"),
            ("other", "Outros"),
        ]
    )
    other_nature_assets = fields.Char("Outra Naturesa")
    other_constants = fields.Selection(
        [("constant", "Quotas Constantes"), ("other", "Outro")]
    )
    other_description_constants = fields.Char("Outro")

    def amortization_before(self, product=None):
        r = int(str(self.date_to)[0:4]) - 1
        r = str(r) + "-01-01"
        for rec in product:
            for k in rec.depreciation_move_ids:
                if str(k.date)[0:4] == r[0:4]:
                    return k.amount_assets_amortization
        return 0.0

    def get_account_mother(self):
        mother_account = self.env["account.account"].search(
            [("code", "in", ["113", "114", "115", "119"])],#"1152", "1139", 
            order="code,name",
        )
        return mother_account

    def get_account_mother_incorp(self):
        mother_account = self.env['account.account'].search(
            [('code', 'in', ['121', '122', '123', '124', '125', '126', '127', '128', '129'])],
            order='code,name')
        return mother_account


    def get_amortization_all(self, code):
        if code[0].code.startswith('1152') or code[0].code.startswith('1139'):# or code[0].code.startswith('1232')
            cod = code[0].code
        else:
            cod = code[0].code #+ "1"

        list_data = []
        list_inf = self.env['account.asset'].search(
            [('acquisition_date', '>=', self.date_from),
             ('acquisition_date', '<=', self.date_to),
             ('state', '=', 'open'),
             ('account_asset_id.code', 'like', cod + '%')],
            order='account_asset_id, name')

        ano_limite = self.date_to.year
        last_asset_depreciated_value = 0.0
        for rec in list_inf:
            tax = abs(round(rec.depreciation_move_ids[0].amount_total*100/rec.original_value, 2))
            valor_before = 0.0
            value_exercice_before = 0.0
            value_exercice = 0.0
                
            for line in rec.depreciation_move_ids.sorted('date'):
                if len(line.name) > 3 and line.date <= self.date_to:
                    valor_before += abs(line.amount_total)
                    if line.date.year < ano_limite:
                        value_exercice_before += abs(line.amount_total)
                    if line.date.year == ano_limite:
                        value_exercice += abs(line.amount_total)
                    last_asset_depreciated_value = abs(line.asset_remaining_value)
                else:
                    break

            values_17 = abs(rec.depreciation_move_ids.sorted('date')[0].asset_depreciated_value if rec.depreciation_move_ids and rec.depreciation_move_ids.sorted('date')[0].name != '/' else 0.0)

            data = {
                'code': rec.account_asset_id.code,
                'name': rec.name,
                'acq_month': str(rec.acquisition_date)[::-1][3:5][::-1] if rec.acquisition_date else " ",
                'acq_year': str(rec.acquisition_date)[0:4] if rec.acquisition_date else " ",
                'opera_m': str(rec.prorata_date)[::-1][3:5][::-1] if rec.prorata_date else " ",
                'opera_y': str(rec.prorata_date)[0:4] if rec.prorata_date else " ",
                'is_import': 'Sim' if str(rec.is_import) else "Não",
                'acquisition_value': rec.original_value,
                'duration': rec.method_number,
                'valor_total_revaluation': rec.original_value,      
                'valor_before': value_exercice_before,
                'tax': tax,
                'tax_corrected': tax,
                'values': values_17,
                'value_exercice': value_exercice,# value_exercice - value_exercice_before, #valor_before - value_exercice_before,
                'value_depreciation': rec.original_value - last_asset_depreciated_value,#valor_before - values_17,
                'value_accounting': last_asset_depreciated_value,#rec.original_value - valor_before + values_17
            }
            list_data.append(data)
        print("Testandoooo: ", sum(rec['value_exercice'] for rec in list_data))
        return {'data': list_data, 'total_original': sum(rec['acquisition_value'] for rec in list_data),
                'valor_total_revaluation': sum(rec['valor_total_revaluation'] for rec in list_data),
                'valor_before': sum(rec['valor_before'] for rec in list_data),
                'values': sum(rec['values'] for rec in list_data),
                'value_depreciation': sum(rec['value_depreciation'] for rec in list_data),
                'value_accounting': sum(rec['value_accounting'] for rec in list_data),
                'value_exercice': sum(rec['value_exercice'] for rec in list_data),
                }

    def amortization_account_move_line(self):
        rec = self.env["account.move.line"].search(
            [
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
                ("account_id.code", "in", ["124", "129"]),
            ],
            order="account_id",
        )
        return rec

    def print(self):
        return self.env.ref(
            "cp_account_report_ao.action_amortization_map_report"
        ).report_action(self)

    def amortization_account_move_line_incorporates(self):
        accounts = self.env["account.account"].search(
            [("reason_code", "=", "12")], order="code"
        )
        l = []
        data_total = {}
        _balance = 0.0
        _balance_before = 0.0
        _balance_total = 0.0
        for rec in accounts:
            for re in rec:
                data = {}
                move_line = self.env["account.move.line"].search(
                    [
                        ("date", ">=", self.date_from),
                        ("account_id", "=", rec.id),
                        ("move_id.state", "=", "posted"),
                        ("balance", "!=", "0"),
                        ("company_id", "=", self.company_id.id),
                    ],
                    order="account_id",
                )
                if move_line:
                    balance = sum(move_line.mapped("balance"))
                    data["name"] = re.name
                    data["code"] = re.code
                    data["balance"] = abs(balance)
                    _balance += abs(balance)
                    data["n1"] = 3
                    data["n2"] = 0
                    data["tax"] = 33.33
                    data["valor_r"] = abs(balance)
                    data["valor_before"] = (
                        self.amortization_account_move_line_incorporates_before(rec.id)
                    )
                    _balance_before += (
                        self.amortization_account_move_line_incorporates_before(rec.id)
                    )
                    data["total_c"] = abs(balance) - abs(
                        self.amortization_account_move_line_incorporates_before(rec.id)
                    )
                    _balance_total += abs(balance) - abs(
                        self.amortization_account_move_line_incorporates_before(rec.id)
                    )
                    l.append(data)
        data_total["balance"] = _balance
        data_total["valor_before"] = _balance_before
        data_total["total"] = _balance_total
        return {"line": l, "total": data_total}

    def amortization_account_move_line_incorporates_before(self, accout):
        r = int(str(self.date_to)[0:4]) - 1
        r = str(r) + "-01-01"
        r2 = int(str(self.date_to)[0:4]) - 1
        r2 = str(r2) + "-12-31"
        move_line = self.env["account.move.line"].search(
            [
                ("date", ">=", r),
                ("date", "<=", r2),
                ("account_id", "=", accout),
                ("move_id.state", "=", "posted"),
                ("balance", "!=", "0"),
                ("company_id", "=", self.company_id.id),
            ],
            order="account_id",
        )
        if move_line:
            balance = sum(move_line.mapped("balance"))
            return balance
        else:
            return 0.0

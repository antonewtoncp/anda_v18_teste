from collections import defaultdict
from pprint import pprint

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import safe_eval
from odoo.tools.misc import formatLang
from odoo.tools.sql import SQL
import base64
import qrcode
from io import BytesIO
from qrcode.constants import ERROR_CORRECT_M
from PIL import Image
import os
from odoo.modules.module import get_module_resource
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"
    _order = "id desc"

    def _default_fiscal_year(self):
        return self.env.company.accounting_year.id

    def _default_fiscal_period(self):
        company_id = self.env.company.id
        return (
            self.env["account.fiscal.period"]
            .search(
                [
                    ("company_id", "=", company_id),
                    ("period", "=", "12"),
                    ("year", "=", self._default_fiscal_year()),
                ]
            )
            .id
        )

    year = fields.Many2one(
        comodel_name="account.fiscal.year", default=lambda l: l._default_fiscal_year()
    )
    period = fields.Many2one(
        comodel_name="account.fiscal.period",
        default=lambda l: l._default_fiscal_period(),
    )
    payment_difference = fields.Float("Diferença de Pagamento")
    cost_center = fields.Many2one(
        comodel_name="account.cost.center", string="Centro de Custos para Faturação"
    )
    has_cost_center = fields.Boolean(related="company_id.invoice_cost_center")
    
    ref_invoice = fields.Char("reference invoice", store=True)

    qr_code = fields.Binary(string="QR Code", compute="_compute_qr_code")

    # def _compute_qr_code(self):
    #     for record in self:
    #         data = f"Fatura Nº: {record.name or ''}\nTotal: {record.amount_total}\nData: {record.invoice_date}"
    #         qr = qrcode.make(data)
    #         buffer = BytesIO()
    #         qr.save(buffer, format='PNG')
    #         record.qr_code = base64.b64encode(buffer.getvalue())


    def _compute_qr_code(self):
        for record in self:
            if not record.name:
                record.qr_code = False
                continue

            # Montar URL conforme especificação AGT
            doc_no = (record.name or "").replace(" ", "%20")
            url = f"https://portaldocontribuinte.minfin.gov.ao/consultar?documentNo={doc_no}"

            qr = qrcode.QRCode(
                version=4,
                error_correction=ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(url.encode("utf-8"))
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

            # Compatibilidade com versões antigas do Pillow
            resample = getattr(Image, "Resampling", Image).LANCZOS
            qr_img = qr_img.resize((350, 350), resample)

            logo_path = get_module_resource("ht_account_ao", "static", "img", "agt_logo.png")
            if logo_path and os.path.exists(logo_path):
                logo = Image.open(logo_path)
                max_logo_size = int(350 * 0.2)
                logo.thumbnail((max_logo_size, max_logo_size), resample)

                qr_width, qr_height = qr_img.size
                logo_width, logo_height = logo.size
                pos = ((qr_width - logo_width) // 2, (qr_height - logo_height) // 2)

                qr_img.paste(logo, pos, mask=logo if logo.mode == "RGBA" else None)

            buffer = BytesIO()
            qr_img.save(buffer, format="PNG")
            record.qr_code = base64.b64encode(buffer.getvalue())



    def _prepare_cost_center(self):
        for res in self:
            if res.cost_center:
                for line in res.sudo().line_ids:
                    line.account_id.has_cost_center = True

    #Voltar a constraint mas permitir quando o contexto vem das amortizações
    # @api.constrains("date", "invoice_date", "year")
    # def validate_date(self):
    #     for res in self:
    #         if res.company_id.accounting_year and res.year:
    #             if res.company_id.accounting_year == res.year:
    #                 if not (res.period.start_date <= res.date <= res.period.end_date):
    #                     raise ValidationError(
    #                         _(
    #                             "A data %s está fora do período %s \n "
    #                             "Inicio: %s - Fim: %s\n Verificar por favor"
    #                         )
    #                         % (
    #                             res.date,
    #                             res.period.name,
    #                             res.period.start_date,
    #                             res.period.end_date,
    #                         )
    #                     )
    #             else:
    #                 raise ValidationError(
    #                     "Ano do registo corrente diferente do Ano fiscal da empresa"
    #                 )

    @api.constrains("cost_center")
    def _check_cost_center(self):
        self._prepare_cost_center()
    
    
      #Cativar iva apenas dos clientes que cativam************************************************************
#     @api.onchange('invoice_line_ids', 'partner_id', 'move_type')
#     def _onchange_invoice_lines_for_iva_cativo(self):
#         if self.move_type != 'out_invoice' or not self.partner_id:
#             return

#         if self.partner_id.iva_cativo != 'yes':
#             return

#         account_cliente = self.partner_id.property_account_receivable_id
#         if not account_cliente:
#             raise UserError(_("O parceiro não tem conta a receber definida."))

#         # Remove linhas existentes do IVA Cativo
#         self.line_ids = self.line_ids.filtered(lambda l: not (
#             l.account_id.code == '34572' and
#             'IVA Cativo' in l.name
#         ))

#         # Calcula o valor do IVA
#         tax = sum(
#         line.price_subtotal * (line.tax_ids.amount / 100)
#         for line in self.invoice_line_ids
#         if line.tax_ids and line.tax_ids.amount_type == 'percent'
#     )
#         if tax <= 0:
#             return

#         account_iva_cativo = self.env['account.account'].search([
#             ('code', '=', '34572'),
#         ], limit=1)

#         if not account_iva_cativo:
#             raise UserError(_("Conta 34572 não existe. Contacte o contabilista."))

#         # Cria linha do IVA Cativo
#         self.env['account.move.line'].new({
#     'move_id': self.id,
#     'account_id': account_iva_cativo.id,
#     'debit': tax,
#     'credit': 0.0,
#     'name': 'IVA Cativo - Débito',
#     'partner_id': self.partner_id.id,
# })
        
        
        # self.invoice_line_ids = self.invoice_line_ids.filtered(
        #        lambda l: l.account_id.code != '34572' and l.price_subtotal > 0
        #      )

    
    

    @api.onchange("year")
    def onchange_year(self):
        for period in self.year.periods:
            if not self.period and period.period == 12:
                self.period = period

    @staticmethod
    def _set_format_sequence_agt(move, date_group):
        if move.move_type in ["in_invoice", "out_invoice", "out_refund", "in_refund"]:
            date_group["format_values"]["seq_length"] = 1
            date_group["format"] = (
                "{prefix1}{year:0{year_length}d}{prefix2}{seq:0{seq_length}d}{suffix}"
            )

    @staticmethod
    def _set_prefix_sequence_agt(move, date_group):
        if move.move_type == "out_invoice":
            date_group["format_values"]["prefix1"] = "FT C"
        if move.move_type == "in_invoice":
            date_group["format_values"]["prefix1"] = "FT F"
        elif move.move_type == "out_refund":
            date_group["format_values"]["prefix1"] = "NC C"
        elif move.move_type == "in_refund":
            date_group["format_values"]["prefix1"] = "NC F"

    @api.depends("posted_before", "state", "journal_id", "date")
    def _compute_name(self):
        def journal_key(move):
            return (move.journal_id, move.journal_id.refund_sequence and move.move_type)

        def date_key(move):
            return (move.date.year, move.date.month)

        grouped = defaultdict(  # key: journal_id, move_type
            lambda: defaultdict(  # key: first adjacent (date.year, date.month)
                lambda: {
                    "records": self.env["account.move"],
                    "format": False,
                    "format_values": False,
                    "reset": False,
                }
            )
        )
        self = self.sorted(lambda m: (m.date, m.ref or "", m.id))
        highest_name = self[0]._get_last_sequence() if self else False

        # Group the moves by journal and month
        for move in self:
            if (
                not highest_name
                and move == self[0]
                and not move.posted_before
                and move.date
            ):
                # In the form view, we need to compute a default sequence so that the user can edit
                # it. We only check the first move as an approximation (enough for new in form view)
                pass
            elif (move.name and move.name != "/") or move.state != "posted":
                try:
                    if not move.posted_before:
                        move._constrains_date_sequence()
                    # Has already a name or is not posted, we don't add to a batch
                    continue
                except ValidationError:
                    # Has never been posted and the name doesn't match the date: recompute it
                    pass
            group = grouped[journal_key(move)][date_key(move)]
            if not group["records"]:
                # Compute all the values needed to sequence this whole group
                move._set_next_sequence()
                group["format"], group["format_values"] = (
                    move._get_sequence_format_param(move.name)
                )
                group["reset"] = move._deduce_sequence_number_reset(move.name)
            group["records"] += move

        # Fusion the groups depending on the sequence reset and the format used because `seq` is
        # the same counter for multiple groups that might be spread in multiple months.
        final_batches = []
        for journal_group in grouped.values():
            journal_group_changed = True
            for date_group in journal_group.values():
                """set format and prefix sequence based AGT"""
                move._set_format_sequence_agt(move, date_group)
                move._set_prefix_sequence_agt(move, date_group)
                if (
                    journal_group_changed
                    or final_batches[-1]["format"] != date_group["format"]
                    or dict(final_batches[-1]["format_values"], seq=0)
                    != dict(date_group["format_values"], seq=0)
                ):
                    final_batches += [date_group]
                    journal_group_changed = False
                elif date_group["reset"] == "never":
                    final_batches[-1]["records"] += date_group["records"]
                elif (
                    date_group["reset"] == "year"
                    and final_batches[-1]["records"][0].date.year
                    == date_group["records"][0].date.year
                ):
                    final_batches[-1]["records"] += date_group["records"]
                else:
                    final_batches += [date_group]

        # Give the name based on previously computed values
        for batch in final_batches:
            for move in batch["records"]:
                move.name = batch["format"].format(**batch["format_values"])
                batch["format_values"]["seq"] += 1
            batch["records"]._compute_split_sequence()

        self.filtered(lambda m: not m.name).name = "/"

    def get_tax_line_details(self):
        """return: data for all taxes"""
        tax_lines_data = []
        for line in self.invoice_line_ids:
            for tax_line in line.tax_ids:
                tax_lines_data.append(
                    {
                        "tax_exigibility": tax_line.tax_exigibility,
                        "tax_amount": line.price_subtotal * (tax_line.amount / 100),
                        "base_amount": line.price_subtotal,
                        "tax": tax_line,
                    }
                )
        return tax_lines_data

    def tax_of_invoice(self):
        taxes = []
        for line in self.invoice_line_ids:
            for tax in line.tax_ids:
                taxes.append(tax)
        return list(set(taxes))

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    @api.constrains("journal_id")
    def _check_line_movement(self):
        if self.env.company.country_code != "AO":
            return
        for line in self.line_ids:
            if (
                line.period.period in ["12", "0", "14", "13"]
                and line.account_id.nature != "M"
            ):
                raise UserError(
                    _(
                        "Apenas contas de movimentos podem ser "
                        "lancadas no período ordinário.\n"
                        "Rever a conta %s-%s"
                        % (line.account_id.code, line.account_id.name)
                    )
                )

    def found_account_account(self, code):
        account = self.env["account.account"].search(
            [("code", "=", code), ("company_ids", "=", self.company_id.id)], limit=1
        )
        if not account:
            raise ValidationError(
                "A conta com {} não foi encontrada\n"
                ""
                "Por favor contactar o contabilista para a criação da conta".format(
                    code
                )
            )
        else:
            return account.id

    def balance_of_one_account(self, code):
        _query = """SELECT SUM(balance)AS balance
                           FROM account_move_line
                           WHERE (reason_code IN %(reason_code)s)
                               AND (date >= %(date_from)s)
                               AND (date <= %(date_to)s)
                               AND(move_id_state='posted')
                               AND (company_id = %(company_id)s)
                               AND(account_code not ilike '{}9')"""
        _code = code
        if not isinstance(code, tuple):
            _code = (code,)
        args = {
            "reason_code": tuple(_code),
            "date_from": self.year.date_from,
            "date_to": self.year.date_to,
            "company_id": self.company_id.id,
        }
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            balance = row["balance"]
        return balance if balance else 0.0

    def query_geral_moviment_end_line(self, code):
        _query = """SELECT SUM(balance)AS balance
                                   FROM account_move_line
                                   WHERE (reason_code = %(reason_code)s)
                                       AND (date >= %(date_from)s)
                                       AND (date <= %(date_to)s)
                                       AND(move_id_state='posted')
                                       AND (company_id = %(company_id)s)
                                        AND(account_code not ilike '{}9')
"""
        args = {
            "reason_code": code,
            "date_from": self.year.date_from,
            "date_to": self.year.date_to,
            "company_id": self.company_id.id,
        }

        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            balance = row["balance"]
        return balance

    def found_moviment(self, cod1, cod2):
        return abs(self.balance_of_one_account(cod1)) - abs(
            self.balance_of_one_account(cod2)
        )

    def create_account_move_line_result_debit(self, code, balance):
        account = self.found_account_account(code)
        move = self.env["account.move.line"].create(
            {
                "move_id": self.id,
                "account_id": account,
                "credit": abs(balance) if balance < 0 else 0.0,
                "debit": abs(balance) if balance > 0 else 0.0,
            }
        )

    def create_account_move_line_result_credit(self, code, balance):
        account = self.found_account_account(code)
        move = self.env["account.move.line"].create(
            {
                "move_id": self.id,
                "account_id": account,
                "credit": abs(balance) if balance > 0 else 0.0,
                "debit": abs(balance) if balance < 0 else 0.0,
            }
        )

    def create_account_move_line_7(self, code, balance):
        account = self.found_account_account(code)
        move = self.env["account.move.line"].create(
            {
                "move_id": self.id,
                "account_id": account,
                "credit": abs(balance) if balance > 0 else 0.0,
                "debit": abs(balance) if balance < 0 else 0.0,
            }
        )

    def sum_reason_start_digit_two(
        self,
    ):
        self.make_clearance_classe_6()
        self.make_clearance_classe_7()
        six = "61", "62", "63", "64", "65"
        seven = "71", "72", "73", "75"
        balance_8219 = self.balance_of_one_account(six) + self.balance_of_one_account(
            seven
        )
        if balance_8219 != 0:
            self.create_account_move_line_result_credit("8219", balance_8219)
        valor_839 = self.found_moviment("66", "76")
        if valor_839:
            self.create_account_move_line_result_debit("839", valor_839)
        valor_849 = self.found_moviment("67", "77")
        if valor_849 != 0.0:
            self.create_account_move_line_result_debit("849", valor_849)

        valor_859 = self.found_moviment("68", "78")
        if valor_859 != 0:
            self.create_account_move_line_result_debit("859", valor_859)
        valor_869 = self.found_moviment("69", "79")
        if valor_869 != 0.0:
            self.create_account_move_line_result_debit("869")
        if balance_8219:
            self.create_account_move_line_result_debit("881", balance_8219)
        if valor_839:
            self.create_account_move_line_result_credit("882", valor_839)
        if valor_849:
            self.create_account_move_line_result_credit("883", valor_849)
        if valor_859:
            self.create_account_move_line_result_credit("884", valor_859)
        if valor_869:
            self.create_account_move_line_result_credit("886", valor_869)
        if balance_8219 < 0:
            k839 = valor_839 * -1 if valor_839 < 0 else valor_839
            k859 = valor_859 * -1 if valor_859 < 0 else valor_859 * -1
            _s = (balance_8219 + k839 + valor_849 + k859) * 0.25
            self.create_account_move_line_result_debit("341", _s)
            self.create_account_move_line_result_credit("871", _s)
            self.create_account_move_line_result_debit("879", _s)
            self.create_account_move_line_result_credit("885", _s)

    #Fecho automático do ano fiscal
    def move_close_year(self):
        balance = []
        self = self.with_context({"check_move_validity": False})
        list_credit = ["8811"]
        list_debit = ["8821","8841", "8851"]
        list_account_result = ["8111"]
        
        for b in list_credit:
            credit_balance = self.get_balance_account_move(b, self.year.date_to, self.year.date_from)[1]
            if credit_balance < 0:
                self.create_account_move_line_result_credit(b, credit_balance)
            else:
                self.create_account_move_line_result_debit(b, credit_balance)
            balance.append(credit_balance)

        for a in list_debit:
            debit_balance = self.get_balance_account_move(a, self.year.date_to, self.year.date_from)[1]
            if debit_balance < 0:
                self.create_account_move_line_result_debit(a, debit_balance)
            else:
                self.create_account_move_line_result_credit(a, debit_balance)
            balance.append(debit_balance)
        
        amount = sum(balance)
            
        if amount > 0:           
            self.create_account_move_line_result_credit(list_account_result[0], amount)
        else:          
            self.create_account_move_line_result_debit(list_account_result[0], amount)
    
    def create_account_move_line(self, code, balance):
        account = self.found_account_account(code)
        move = self.env["account.move.line"].create(
            {
                "move_id": self.id,
                "account_id": account,
                "credit": abs(balance) if balance < 0 else 0.0,
                "debit": abs(balance) if balance > 0 else 0.0,
            }
        )

    def make_clearance_classe_6(self):
        reason_six = ["61", "62", "63", "64", "65", "66", "67", "68", "69"]
        balance_digit_two = 0.0
        for rec in reason_six:
            balance = self.query_geral_moviment_end_line(rec)
            if balance:
                account = self.found_account_account(rec + "9")
                move = self.env["account.move.line"].create(
                    {
                        "move_id": self.id,
                        "account_id": account,
                        "credit": abs(balance) if balance > 0 else 0.0,
                        "debit": abs(balance) if balance < 0 else 0.0,
                    }
                )
                if rec in reason_six[:5]:
                    self.create_account_move_line("82" + rec[-1], balance)
                    balance_digit_two += balance
                elif rec == "66":
                    self.create_account_move_line("831", balance)
                elif rec == "67":
                    self.create_account_move_line("841", balance)
                elif rec == "68":
                    self.create_account_move_line("851", balance)
                elif rec == "69":
                    self.create_account_move_line("861", balance)

    def create_account_move_line(self, code, balance):
        account = self.found_account_account(code)
        move = self.env["account.move.line"].create(
            {
                "move_id": self.id,
                "account_id": account,
                "credit": abs(balance) if balance < 0 else 0.0,
                "debit": abs(balance) if balance > 0 else 0.0,
            }
        )

    def make_clearance_classe_7(self):
        reason_seven = ["71", "72", "73", "75", "76", "77", "78", "79"]
        balance_digit_two = 0.0
        for rec in reason_seven:
            balance = self.query_geral_moviment_end_line(rec)
            if balance:
                self.create_account_move_line_7(rec + "9", balance)
                if rec == "71":
                    self.create_account_move_line("826", balance)
                    balance_digit_two += balance
                elif rec == "72":
                    self.create_account_move_line("827", balance)
                    balance_digit_two += balance
                elif rec == "73":
                    self.create_account_move_line("828", balance)
                    balance_digit_two += balance
                elif rec == "75":
                    print("saldo da ", balance)
                    self.create_account_move_line("829", balance)
                    balance_digit_two += balance
                elif rec == "76":
                    self.create_account_move_line("832", balance)
                elif rec == "77":
                    self.create_account_move_line("842", balance)
                elif rec == "78":
                    self.create_account_move_line("852", balance)
                elif rec == "79":
                    self.create_account_move_line("862", balance)

    def make_clearance(self, date_to, date_from):
        self = self.with_context({"check_move_validity": False})
        self.sum_reason_start_digit_two()

    def make_close_year(self, date_to, date_from):
        self = self.with_context({"check_move_validity": False})
        self.move_close_year()

    def create_account_move(self, code, date_to, date_from):
        account = self.env["account.account"].search([("code", "=", code)], limit=1)
        move_line = self.env["account.move.line"].search(
            [
                ("move_id.state", "=", "posted"),
                ("move_id.date", ">=", date_from),
                ("move_id.date", "<=", date_to),
                ("account_id.code", "=", code),
                ("balance", "!=", "0"),
                ("company_ids", "=", self.company_id.id),
            ]
        )
        credit, debit = sum(move_line.mapped("credit")), sum(move_line.mapped("debit"))
        move = self.env["account.move.line"].create(
            {
                "move_id": self.id,
                "account_id": account.id,
                "credit": credit,
                "debit": debit,
            }
        )
        balance = credit - debit
        return move, balance

    def create_clearence_iva_credit(self, code, amount):
        account = self.env["account.account"].search(
            [
                ("code", "=", code),
            ],
            limit=1,
        )
        if not account:
            raise ValidationError(
                (
                    "Por favor contactor o contabilista para criar a conta {}".format(
                        code
                    )
                )
            )
        move = self.env["account.move.line"].create(
            {
                "move_id": self.id,
                "account_id": account.id,
                "credit": abs(amount),
                "debit": 0.0,
            }
        )

    def create_clearence_iva_debit(self, code, amount):
        account = self.env["account.account"].search(
            [
                ("code", "=", code),
            ],
            limit=1,
        )
        if not account:
            raise ValidationError(
                (
                    "Por favor contactor o contabilista para criar a conta {}".format(
                        code
                    )
                )
            )
        move = self.env["account.move.line"].create(
            {
                "move_id": self.id,
                "account_id": account.id,
                "credit": 0.0,
                "debit": abs(amount),
            }
        )

    # def make_iva_clerance(self, date_to, date_from):
    #     balance = []
    #     self = self.with_context({"check_move_validity": False})
    #     list_account = ["34531", "34551", "34561"]
    #     list_iva_suportado = ("34511", "34512", "34513")
    #     list_iva_dedutivel = ("34521", "34522", "34523")
    #     for a in list_iva_suportado:
    #         balance.append(self.create_account_move(a, date_to, date_from)[1])
    #     for b in list_iva_dedutivel:
    #         balance.append(self.create_account_move(b, date_to, date_from)[1])
    #     amount = sum(balance)
    #     if amount > 0:
    #         self.create_clearence_iva_debit(list_account[0], amount)
    #         self.create_clearence_iva_credit(list_account[1], amount)
    #         self.create_clearence_iva_debit(list_account[2], amount)
    #     else:
    #         self.create_clearence_iva_credit(list_account[0], amount)
    #         self.create_clearence_iva_debit(list_account[1], amount)
    #         self.create_clearence_iva_credit(list_account[2], amount)
    def make_iva_clerance(self, date_to, date_from):
        # balance = []
        # self = self.with_context({"check_move_validity": False})
        # list_account = ["34531", "34551", "34561"]
        # list_iva_suportado = ("34511", "34512", "34513")
        # list_iva_dedutivel = ("34521", "34522", "34523")
        # for a in list_iva_suportado:
        #     balance.append(self.create_account_move(a, date_to, date_from)[1])
        # for b in list_iva_dedutivel:
        #     balance.append(self.create_account_move(b, date_to, date_from)[1])
        # amount = sum(balance)
        # if amount > 0:
        #     self.create_clearence_iva_debit(list_account[0], amount)
        #     self.create_clearence_iva_credit(list_account[1], amount)
        #     self.create_clearence_iva_debit(list_account[2], amount)
        # else:
        #     self.create_clearence_iva_credit(list_account[0], amount)
        #     self.create_clearence_iva_debit(list_account[1], amount)
        #     self.create_clearence_iva_credit(list_account[2], amount)
        balance = []
        self = self.with_context({"check_move_validity": False})
        list_iva_credit = ("34521", "34522", "34523", "34541", "34571", "345231512","345231411","34523111","34572", "345231511") #IVA dedutível, Regularizações a favor do sujeito passivo, e a recuperar
        list_iva_debit = ("34531","34532", "34533", "34534", "34542") #IVA liqlist_iva_debituidado, e Regularizações a favor do estado
        list_iva_account_result = ["34561", "34571", "34551"] #IVA a pagar de apuramento, a recuperar de apuramento, e IVA-Apuramento
        debit = 0
        for a in list_iva_debit:
            debit_balance = self.get_balance_account_move(a, date_to, date_from)[1]
            debit = debit + debit_balance
            self.create_clearence_iva_debit(a, debit_balance)
            balance.append(debit_balance) 
        credit = 0
        for b in list_iva_credit:
            credit_balance = self.get_balance_account_move(b, date_to, date_from)[1]
            credit = credit + credit_balance
            self.create_clearence_iva_credit(b, credit_balance)
            balance.append(credit_balance)

        amount = sum(balance)

        if credit > debit:
            self.create_clearence_iva_debit(list_iva_account_result[2], amount)
            self.create_clearence_iva_credit(list_iva_account_result[2], amount)
        else:
            self.create_clearence_iva_credit(list_iva_account_result[2], amount)
            self.create_clearence_iva_debit(list_iva_account_result[2], amount)
            
        if amount > 0:           
            self.create_clearence_iva_credit(list_iva_account_result[0], amount)

        else:          
            self.create_clearence_iva_debit(list_iva_account_result[1], amount)

    def get_balance_account_move(self, code, date_to, date_from):
        move_line = self.env["account.move.line"].search(
            [
                ("move_id.state", "=", "posted"),
                ("move_id.date", ">=", date_from),
                ("move_id.date", "<=", date_to),
                ("account_code", "=", code),
                ("balance", "!=", "0"),
                ("company_id", "=", self.company_id.id),
            ]
        )
        credit, debit = sum(move_line.mapped("credit")), sum(move_line.mapped("debit"))
        balance = credit - debit
        return True, balance


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _order = "id asc"
    cash_flow = fields.Many2one(
        string="Fluxo de Caixa", related="account_id.cash_flow", store=True
    )
    iva_plan = fields.Many2one(
        string="Plano de Iva", related="account_id.iva_plan", store=True
    )
    fiscal_plan = fields.Many2one(
        string="Plano Fiscal", related="account_id.fiscal_plan", store=True
    )
    has_cost_center = fields.Boolean(related="account_id.has_cost_center")
    has_cash_flow = fields.Boolean(related="account_id.has_cash_flow")
    has_iva = fields.Boolean(related="account_id.has_iva")
    has_fiscal_plan = fields.Boolean(related="account_id.has_fiscal_plan")
    move_id_state = fields.Selection(related="move_id.state", string="state")
    period = fields.Many2one(
        comodel_name="account.fiscal.period", compute="_store_period", store=True
    )
    cost_center = fields.Many2one(
        comodel_name="account.cost.center",
        related="move_id.cost_center",
        string="Cost Center",
        store=True,
    )

    @api.depends("move_id")
    def _store_period(self):
        for res in self:
            if res.move_id.period:
                res.period = res.move_id.period



class CashFlowReportCustomHandler(models.AbstractModel):
    _inherit = 'account.cash.flow.report.handler'
    _description = 'Customização do Cash Flow Report Handler'

    def _compute_liquidity_balance(self, report, options, payment_account_ids, date_scope):
        _logger.info("🔥 Entrou na minha versão customizada de _compute_liquidity_balance")

        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(
                column_group_options,
                date_scope,
                domain=[('account_id', 'in', payment_account_ids)]
            )

            account_alias = query.join(
                lhs_alias='account_move_line',
                lhs_column='account_id',
                rhs_table='account_account',
                rhs_column='id',
                link='account_id'
            )

            account_name = self.env['account.account']._field_to_sql(account_alias, 'name', query)
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            code_store   = self.env['account.account']._field_to_sql(account_alias, 'code_store', query)

            queries.append(SQL(
                '''
                SELECT
                    %(column_group_key)s AS column_group_key,
                    account_move_line.account_id,
                    %(account_code)s AS account_code,
                    %(account_name)s AS account_name,
                    %(code_store)s AS code_store,
                    SUM(%(balance_select)s) AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                WHERE %(search_condition)s
                GROUP BY 
                    account_move_line.account_id, 
                    %(account_code)s, 
                    %(account_name)s, 
                    %(code_store)s
                ''',
                column_group_key=column_group_key,
                account_code=account_code,
                account_name=account_name,
                code_store=code_store,
                table_references=query.from_clause,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
            ))

        final_query = SQL(' UNION ALL ').join(queries)
        _logger.info("🔥 SQL FINAL: %s", final_query)

        self._cr.execute(final_query)
        return self._cr.dictfetchall()

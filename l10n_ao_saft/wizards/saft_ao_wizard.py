# -*- coding: utf-8 -*-
from ..models import utils
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from copy import deepcopy
from collections import defaultdict
from odoo.tools import float_repr
from odoo import api, fields, models, release, _
from pprint import pprint
from datetime import datetime
from xml.dom.minidom import parseString

import collections
import collections.abc
collections.Iterable = collections.abc.Iterable  # 🔧 patch rápido

from dicttoxml import dicttoxml

file_types = [
    ('F', 'Faturação'),
    ('A', 'Aquisição de bens e serviços'),
]


class SafTWizard(models.TransientModel):
    _name = "saft.ao.wizard"
    _description = "Generate XML File"

    type = fields.Selection(
        string="File Type", selection=file_types, help="Tipo do ficheiro de exportação")
    comment = fields.Text("Comment")
    company_id = fields.Many2one(string="Company", comodel_name="res.company", required=True,
                                 default=lambda l: l.env.user.company_id)
    date_from = fields.Date("Start Date")
    date_to = fields.Date("End Date")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    content_xml = fields.Text("")
    name = fields.Char("Name", compute='_compute_name')
    option = fields.Selection([('without_problem', 'Good'), ('With_problem', 'Bad')],
                              default='without_problem', string='Situation Of Database')

    @api.depends('date_to', 'date_from')
    def _compute_name(self):
        self.name = "XML SAF-T AO PERIOD %s - %s" % (
            self.date_to or '/',
            self.date_from or '/'
        )

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        if self.date_from > self.date_to:
            raise ValidationError('Start Date must be lower than End Date')

    def get_customer(self):
        customer = self.env['res.partner'].search([('customer', '=', True)])
        return customer

    def get_movement_article(self):
        articles = self.env['stock.move.line'].search(
            [('state', '=', 'done')])
        return articles

    def get_account_tax(self):
        taxes = self.env['account.tax'].search(
            [('active', '=', True)])
        return taxes

    @staticmethod
    def check_product_type(product_type):
        if product_type in ['service', 'monthly']:
            return 'S'
        return 'P'

    def check_saft_tax(self, tax_lines, tax_mapped):
        _tax = None
        last_tax_amount = 0
        for tax in tax_lines:
            if tax_mapped.count(tax.tax_on) > 1:
                last_tax_amount = 0
                for tax_use in tax_lines.filtered(lambda l: l.tax_on == tax.tax_on):
                    if last_tax_amount == 0:
                        if tax_use.amount >= last_tax_amount:
                            _tax = tax_use
                            last_tax_amount = tax_use.amount
                    else:
                        if tax_use.amount >= last_tax_amount:
                            _tax |= tax_use
                            last_tax_amount = tax_use.amount
            else:
                if _tax:
                    _tax |= tax
                else:
                    _tax = tax
        return _tax

    def get_customer_id(self, customer):
        if not customer.vat:
            final_consumer = self.env['res.partner'].search(
                [('vat', '=', '999999999')])
            if final_consumer:
                customer = final_consumer[0]
        final_consumer = self.env['res.partner'].search([('ref', '=', 'CF')])
        if final_consumer:
            customer = final_consumer[0]
        return customer.ref

    @api.model
    def _fill_saft_report_payments_values(self, options, values):

        result = {
            'payments': {
                "number_of_entries": 0,
                "total_debit": 0,
                "total_credit": 0,
                "payment": [],
            }
        }

        payment_data = {}

        invoices = self.env['account.move'].search([("invoice_date", ">=", options['date']['date_from']),
                                                    ("invoice_date", "<=",
                                                     options['date']['date_to']),
                                                    ('company_id', '=',
                                                     self.env.company.id),
                                                    ('move_type', 'in', [
                                                        'out_invoice', 'out_refund']),
                                                    ('state', 'in', ['posted']),
                                                    ("system_entry_date", "!=", None)],
                                                   order="create_date asc")

        payments_ = []
        payments = []
        for inv in invoices:
            for payment_rec in self.env['account.payment'].search([("ref", '=', inv.name)]):
                payments_.append(payment_rec)

        for item in payments_:
            if item.id:
                payments.append(item)

        for payment in payments:
            if payment.id:
                payment_status = 'N'
                if payment.state == 'cancelled':
                    payment_status = 'A'

                lined = payment.mapped("line_ids")

                move = self.env['account.move'].search(
                    [("name", '=', payment.ref)])

                payment_data = {
                    "payment_ref_no": str(payment.receipt_no).replace((str(move.invoice_date).split('-'))[0], '20'),
                    "period": utils.extract_period(move.invoice_date),
                    "transaction_id": "%s %s %s" % (
                        str(move.invoice_date), str(payment.journal_id.code).replace(' ', ''),
                        str(payment.name).replace('/', '').replace(' ', '')),
                    "transaction_date": move.invoice_date,
                    "payment_type": 'RG',
                    "description": 'P ' + str(payment.invoice_line_ids.mapped('move_name')),
                    "system_id": payment.name,
                    "document_status": {
                        "payment_status": payment_status,
                        "payment_status_date": str((move.invoice_date).strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T'),

                        # "payment_status_date": str((payment.system_entry_date).strftime("%Y-%m-%d %H:%M:%S")).replace(
                        #     ' ',
                        #     'T') if payment.system_entry_date else str(
                        #     move.invoice_date.strftime("%Y-%m-%d %H:%M:%S")).replace(
                        #     ' ',
                        #     'T'),
                        # "Reason": "",
                        "source_id": payment.create_uid.id,
                        "source_payment": 'P',
                    },
                    "payment_method": {
                        "payment_mechanism": payment.payment_mechanism or 'TB',
                        "payment_amount": utils.gross_total(payment.amount),
                        "date": payment.date,
                    },
                    "source_id": payment.create_uid.id,
                    "system_entry_date": str((move.invoice_date).strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T'),
                    "customer_id": 'CF',
                    "line": []
                }

                lined_in = self.env['account.move'].search(
                    [("name", '=', payment.ref), ('move_type', 'in', ['out_invoice'])], order="invoice_date asc")

                for line in lined_in.line_ids:
                    if line.tax_ids:
                        lines = {
                            "line_number": line.id,
                            "source_document_id": {
                                "originating_on": payment.name,
                                "invoice_date": move.invoice_date,
                                "description": payment.ref or payment.name,
                            },
                            "settlement_amount": sum(line.mapped("discount")),
                            "taxs": [],

                        }

                        if move.move_type == "out_refund" and move.payment_state in ["not_open", "paid", "partial",
                                                                                     "reversed"]:
                            lines["debit_amount"] = move.amount_untaxed
                        elif move.move_type == "out_invoice" and move.payment_state in ["not_open", "paid", "partial",
                                                                                        "reversed"]:
                            lines["credit_amount"] = move.amount_untaxed

                        for tax in line.tax_ids:
                            if tax.tax_on == "invoice":
                                lines["taxs"].append({
                                    "tax_type": tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS',
                                                                                           'IS'] else "IVA",
                                    # FIXME: 4.1.4.19.15.2.
                                    "tax_country_region": tax.country_region,
                                    "tax_code": tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS',
                                                                                           'IS'] else tax.saft_tax_code,
                                    'tax_percentage': tax.amount if tax.amount_type in ["percent", "division"] else "0"
                                })

                        for tax in line.tax_ids:
                            if tax.tax_on == "invoice":
                                lines[
                                    "tax_exemption_reason"] = tax.exemption_reason if tax.amount == 0 and tax.exemption_reason else False
                                lines['tax_exemption_code'] = "M21" if tax.amount == 0 else ""
                        payment_data["line"].append(lines)

                payment_data["document_totals"] = {
                    "tax_payable": utils.gross_total(move.amount_tax),
                    "tax_payables": utils.gross_total(inv.amount_untaxed * 0.065),
                    "net_total_w": utils.gross_total(inv.amount_untaxed) - utils.gross_total(
                        inv.amount_untaxed * 0.065),

                    "net_total": utils.gross_total(move.amount_untaxed),
                    "gross_total": utils.gross_total(move.amount_total),
                    "settlement": {
                        "settlement_amount": 0.0,
                    },
                }

                if lined.currency_id != lined.company_id.currency_id:
                    payment_data["document_totals"]["currency"] = {
                        "currency_code": lined.currency_id.name,
                        "currency_amount": lined.amount_total,
                        "exchange_rate": lined.currency_id.rate
                    }

                if move.move_type == "out_refund" and move.payment_state in ["not_paid", "paid", "partial", "reversed"]:
                    result["payments"]["total_debit"] += utils.gross_total(
                        move.amount_untaxed)
                elif move.move_type == "out_invoice" and move.payment_state in ["not_paid", "paid", "partial",
                                                                                "reversed"]:
                    result["payments"]["total_credit"] += utils.gross_total(
                        move.amount_untaxed)

            result['payments']['payment'].append(payment_data)
        result['payments']['number_of_entries'] = len(payments)
        # for rec in result['payments']['payment']:
        #     for re in rec['line']:
        #         print(re)
        values.update(result)

    @api.model
    def _fill_saft_report_sales_order_values(self, options, values):

        result = {
            'working_documents': {
                "number_of_entries": 0,
                "total_debit": 0,
                "total_credit": 0,
                "work_documents": [],
            }
        }

        sales = self.env['sale.order'].search([("date_order", ">=", options['date']['date_from']),
                                               ("date_order", "<=", options['date']['date_to']),
                                               ('company_id', '=',
                                                self.env.company.id),
                                               ('state', 'in', [
                                                   'sale'])
                                               ],
                                              order="name asc")
        for sale in sales:
            status_code = 'N'
            if sale.state == 'cancel':
                status_code = 'A'
            if sale.state in ['sale', 'done']:
                status_code = 'F'
            source_billing = "P"
            sale_order = {
                "document_number": sale.work_type + " " + sale.name.split(' ')[-1],
                "document_status": {
                    "work_status": status_code,
                    "work_status_date": str((sale.date_order).strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T'),
                    "source_id": sale.user_id.id,
                    "source_billing": source_billing,
                },
                "hash": sale.hash,
                "hash_control": "0" or sale.hash_control,
                "period": utils.extract_period(sale.create_date),
                "work_date": str(sale.date_order)[0:10],
                "work_type": sale.work_type,
                "source_id": sale.user_id.id,
                "system_entry_date": str((sale.system_entry_date.strftime("%Y-%m-%d %H:%M:%S")).replace(' ',
                                                                                                        'T') if sale.system_entry_date else str(
                    sale.date_order.strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T')),
                "customer_id": 'CF',
                "lines": [],
                "document_totals": {
                    "tax_payable": utils.gross_total(sale.amount_tax),
                    "tax_payables": utils.gross_total(sale.amount_untaxed * 0.065),
                    "net_total_w": utils.gross_total(sale.amount_untaxed) - utils.gross_total(
                        sale.amount_untaxed * 0.065),
                    "net_total": utils.gross_total(sale.amount_untaxed),
                    "gross_total": utils.gross_total(sale.amount_total),
                }

            }

            for line in sale.order_line:

                lines = {
                    "line_number": line.id,
                    "product_code": line.product_id.id or line.product_id.default_code,
                    "product_description": line.product_id.name[:200] if line.product_id.name else "-",
                    "quantity": line.product_uom_qty,
                    "unit_of_measure": "UN",
                    "unit_price": line.price_unit if line.discount == 0 else utils.gross_total(line.price_subtotal),
                    "tax_base": line.price_subtotal if line.price_unit == 0.0 else 0.0,
                    "tax_point_date": str(sale.date_order)[0:10],
                    "description": line.product_id.name[:200] if line.product_id.name else "-",
                    "credit_amount": utils.gross_total(line.price_subtotal),
                    "taxs": [],
                }
                taxes_to_use = self.check_saft_tax(
                    line.tax_id, line.tax_id.mapped('tax_on'))
                if taxes_to_use:
                    for tax in taxes_to_use:
                        if tax.tax_on != 'withholding':
                            tax_values = {
                                "tax_type": tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS',
                                                                                       'IS'] else "IVA",
                                # FIXME: 4.1.4.19.15.2.
                                "tax_country_region": tax.country_region,
                                # "tax_code": tax.tax_type if tax.tax_code == 'NS' else tax.tax_code,
                                "tax_code": tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS',
                                                                                       'IS'] else tax.saft_tax_code,
                            }
                            if tax.amount_type in ["percent", "division"]:
                                tax_values["tax_percentage"] = utils.gross_total(
                                    tax.amount)
                            elif tax.amount_type in ["fixed"]:
                                tax_values["tax_amount"] = utils.gross_total(
                                    tax.amount)
                            if tax.tax_on == "invoice":
                                if tax.amount == 0:
                                    lines["tax_exemption_reason"] = tax.exemption_reason,
                                    lines["tax_exemption_code"] = "M21" if tax.amount == 0 else " ",
                            lines["taxs"].append(tax_values)
                if not lines["taxs"]:
                    lines["taxs"].append({"tax_type": "NS",
                                          "tax_country_region": "AO",
                                          "tax_code": "NS",
                                          "tax_percentage": "0"})
                    lines["tax_exemption_reason"] = "Isento nos termos da alínea l) do nº1 do artigo 12.º do CIVA"
                    lines["tax_exemption_code"] = "M21"
                lines["settlement_amount"] = line.discount

                if not lines["taxs"]:
                    lines["taxs"].append({
                        "tax_type": "NS",
                        "tax_country_region": "AO",
                        "tax_code": "NS",
                        "tax_percentage": "0"})
                    lines["tax_exemption_reason"] = "Isento nos termos da alínea l) do nº1 do artigo 12.º do CIVA"
                    lines["tax_exemption_code"] = "M21"

                sale_order["lines"].append(lines)

            result['working_documents']["work_documents"].append(sale_order)
            result['working_documents']["total_credit"] += utils.gross_total(
                sale.amount_untaxed)

            result['working_documents']["number_of_entries"] += 1
        values.update(result)

    @api.model
    def _fill_saft_report_products_values(self, options, values):
        res = {
            'product_vals_list': []
        }
        default_product = {
            'product_type': 'S',
            'product_code': 'HS12D',
            'product_group': 'Todos',
            'product_description': 'Serviços',
            'product_number_code': 'HS12D',
            # 'CustomsDetails': product.customs_details or "",
        }

        for product in self.env['product.product'].search([]):
            product_val = {
                'product_type': self.check_product_type(product['type']),
                'product_code': str(product['id']).strip()[:60],
                'product_group': product['categ_id']['name'],
                'product_description': str(product['description_sale']).strip()[:200] if product[
                    'description_sale'] else
                str(product['name']).strip()[:200],
                'product_number_code': str(product['barcode']).strip()[:60] if product['barcode'] else str(
                    product['id']).strip()[:60],
                # 'CustomsDetails': product.customs_details or "",
            }
            res['product_vals_list'].append(product_val)
        res['product_vals_list'].append(default_product)

        values.update(res)

    @api.model
    def _fill_saft_report_general_ledger_values(self, options, values):

        result = {
            "sales_invoices": {
                "number_of_entries": 0,
                "total_debit": 0,
                "total_credit": 0,
                "invoices": [],
            },
            "purchase_invoices": {
                "number_of_entries": 0,
                "invoices_p": [],
            },

        }

        # Sales Invoicing
        invoices = self.env['account.move'].search([("invoice_date", ">=", options['date']['date_from']),
                                                    ("invoice_date", "<=", options['date']['date_to']),
                                                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                                                    ('company_id', '=', self.env.company.id),
                                                    ('state', '=', 'posted'),
                                                    ("system_entry_date", "!=", None)
                                                    ],
                                                   order="create_date asc")
        if self.option == 'With_problem':
            invoices.clean_number_invoices(self.date_from, self.date_to)

        for inv in invoices:
            status_code = 'N'
            if inv.state == 'cancel':
                status_code = 'A'
            elif inv.journal_id.self_billing is True:
                status_code = 'S'
            source_billing = "P"

            # FACTURAS CLIENTES

            if inv.move_type in ["out_invoice"]:
                invoice_customer = {
                    "invoice_no": inv.name if self.option == 'without_problem' else inv.sequence_saft_invoice,
                    "document_status": {
                        "invoice_status": status_code,
                        "invoice_status_date": str(inv.system_entry_date).replace(' ',
                                                                                  'T') if inv.system_entry_date else str(
                            inv.create_date).replace(' ', 'T'),
                        # "Reason": "",  # TODO GENERATE CONTENT FOR REASON
                        "source_id": inv.user_id.id,
                        "source_billing": source_billing,
                    },
                    "hash": inv.hash if self.option == 'without_problem' else inv.has_with_problem,
                    "hash_control": inv.hash_control,
                    "period": int(str(inv.invoice_date)[5:7]),
                    "invoice_date": inv.invoice_date,
                    "invoice_type": "FT" if inv.move_type == "out_invoice" else "NC",
                    'order_references': inv.name,

                    "special_regimes": {
                        "self_billing_indicator": 1 if inv.journal_id.self_billing else 0,
                        "cash_vat_scheme_indicator": 1 if inv.company_id.tax_exigibility else 0,
                        "third_parties_billing_indicator": 0,
                    },
                    "source_id": inv.user_id.id,
                    # "EACCode": "N/A",
                    "system_entry_date": str(inv.system_entry_date).replace(' ', 'T') if inv.system_entry_date else str(
                        inv.create_date).replace(' ', 'T'),
                    "transaction_id": "%s %s %s" % (
                        inv.date, inv.journal_id.code.replace(' ', ''),
                        inv.name.replace(' ', '').replace('/', '')) if inv.name else '',
                    "customer_id": 'CF',
                    # "ShipTo": "",  # TODO: 4.1.4.15
                    # "ShipFrom": "",  # TODO: 4.1.4.16
                    # "MovementEndTime": "",  # TODO: 4.1.4.17,
                    # TODO: 4.1.4.18,
                    "movement_start_time": str(inv.system_entry_date).replace(' ',
                                                                              'T') if inv.system_entry_date else str(
                        inv.create_date).replace(' ', 'T'),
                    "lines": [],
                    "document_totals": {
                        "tax_payable": utils.gross_total(inv.amount_tax),
                        "tax_payables": utils.gross_total(inv.amount_untaxed * 0.065),
                        "net_total_w": utils.gross_total(inv.amount_untaxed) - utils.gross_total(
                            inv.amount_untaxed * 0.065),
                        "net_total": utils.gross_total(inv.amount_untaxed),
                        # TODO: we must review this with invoice in different currency
                        "gross_total": utils.gross_total(inv.amount_total),
                        # TODO: we must review this with invoice in different currency
                        "currency": {
                            "currency_code": inv.currency_id.name,
                            "Currency_amount": utils.gross_total(inv.amount_total),
                            "exchange_rate": inv.currency_id.rate,
                        } if inv.currency_id != inv.company_id.currency_id else {},
                        "settlement": {
                            "settlement_discount": inv.settlement_discount or 0,
                            "settlement_amount": inv.settlement_amount or 0,
                            # "SettlementDate": inv.settlement_date or "",
                            "payment_terms": inv.payment_ids.name if inv.payment_ids.name else "",
                        },
                        "payments": [{
                            "payment_mechanism": payment.payment_mechanism or "TB",
                            "payment_amount": utils.gross_total(payment.amount),
                            "date": payment.date,
                        } for payment in inv.payment_ids]

                    },
                    "withholding_tax": [{
                        "withholding_tax_type": tax.tax_id.saft_wth_type,
                        "withholding_tax_description": tax.tax_id.name,
                        "withholding_tax_amount": utils.gross_total(tax.amount),
                    } for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")],
                }
                if not invoice_customer['document_totals']['payments']:
                    invoice_customer['document_totals'].pop('payments')

                # payments = []
                # for payment in inv.payment_ids:
                #     payment_values = {
                #         "PaymentMechanism": payment.payment_mechanism,
                #         "PaymentAmount": utils.gross_total(payment.amount),
                #         "PaymentDate": payment.date,
                #     }
                #     payments.append(payment_values)
                # invoice_customer['DocumentTotals']['Payment'] = payments

                for line in inv.invoice_line_ids:
                    lines = {
                        "line_Number": line.id,
                        # "OrderReferences": {"OriginatingON": inv.origin or "", "OrderDate": ""},  # TODO:4.1.4.19.2.
                        "product_code": line.product_id.id if line.product_id else 'HS12D',
                        "product_description": str(line.product_id.description_sale).strip()[
                                               :200] if str(line.product_id.description_sale) else str(
                            line.product_id.name).strip()[
                                                                                                   :200],
                        "quantity": line.quantity,
                        "unit_of_measure": line.product_uom_id.name if line.product_uom_id.name else "unidade",
                        "unit_price": line.price_unit,
                        "tax_base": line.price_subtotal if line.price_unit == 0.0 else 0.0,
                        "tax_point_date": inv.date,
                        "references": {
                            "reference": inv.ref_invoice if inv.move_type == "out_refund" else "",
                        },
                        "credit_amount": False,
                        "debit_amount": False

                    }

                    # if inv.move_type == "out_refund":
                    #     lines['references'] = {
                    #         "reference": inv.ref_invoice,
                    #     }

                    lines['description'] = str(line.product_id.name).strip()[:200],
                    # lines['ProductSerialNumber'] = {
                    #     "SerialNumber": line.product_id.default_code or "S/N",  # TODO: 4.1.4.19.12.
                    # }

                    if inv.move_type == "out_refund" and inv.payment_state in ["not_paid", "paid", "partial",
                                                                               "reversed"]:
                        lines["debit_amount"] = utils.gross_total(
                            line.price_subtotal)

                    if inv.move_type == "out_invoice" and inv.payment_state in ["not_paid", "paid", "partial",
                                                                                "reversed"]:
                        lines["credit_amount"] = utils.gross_total(
                            line.price_subtotal)

                    lines["tax"] = []

                    taxes_to_use = self.check_saft_tax(
                        line.tax_ids, line.tax_ids.mapped('tax_on'))
                    if taxes_to_use:
                        for tax in taxes_to_use:
                            if tax.tax_on != 'withholding':
                                tax_values = {
                                    "tax_type": tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS',
                                                                                           'IS'] else "IVA",
                                    # FIXME: 4.1.4.19.15.2.
                                    "tax_country_region": tax.country_region,
                                    # "tax_code": tax.tax_type if tax.tax_code == 'NS' else tax.tax_code,
                                    "tax_code": tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS',
                                                                                           'IS'] else tax.saft_tax_code,
                                }
                                if tax.amount_type in ["percent", "division"]:
                                    tax_values["tax_percentage"] = utils.gross_total(
                                        tax.amount)
                                elif tax.amount_type in ["fixed"]:
                                    tax_values["tax_amount"] = utils.gross_total(
                                        tax.amount)
                                if tax.tax_on == "invoice":
                                    if tax.amount == 0:
                                        lines["tax_exemption_reason"] = tax.exemption_reason,
                                        lines["tax_exemption_code"] = "M21" if tax.amount == 0 else " ",
                                lines["tax"].append(tax_values)
                    if not lines["tax"]:
                        lines["tax"].append({"tax_type": "NS",
                                             "tax_country_region": "AO",
                                             "tax_code": "NS",
                                             "tax_percentage": "0"})
                        lines["tax_exemption_reason"] = "Isento nos termos da alínea l) do nº1 do artigo 12.º do CIVA"
                        lines["tax_exemption_code"] = "M21"
                    lines["settlement_amount"] = line.discount
                    # lines["CustomsInformation"] = {  # TODO: 4.1.4.19.19.
                    #     "ARCNo": "",
                    #     "IECAmount": "",
                    # }
                    invoice_customer["lines"].append(lines)

                if inv.currency_id == inv.company_id.currency_id:
                    invoice_customer["document_totals"].pop("currency")

                if not [tax.id for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")]:
                    invoice_customer.pop("withholding_tax")

                result["sales_invoices"]["invoices"].append(invoice_customer)

                if inv.move_type == "out_refund":
                    result["sales_invoices"]["total_debit"] += utils.gross_total(
                        inv.amount_untaxed)

                # if is normal or invoiced
                elif inv.move_type == "out_invoice" and inv.payment_state in ["not_paid", "paid", "partial",
                                                                              "reversed"]:
                    result["sales_invoices"]["total_credit"] += utils.gross_total(
                        inv.amount_untaxed)

                result["sales_invoices"]["number_of_entries"] += 1

        # Purchase Invoicing

        invoices_p = self.env['account.move'].search([("invoice_date", ">=", options['date']['date_from']),
                                                      ("invoice_date", "<=", options['date']['date_to']),
                                                      ('move_type', '=', 'in_invoice'),
                                                      ('company_id', '=', self.env.company.id),
                                                      ('state', '=', 'posted'),
                                                      ("system_entry_date", "!=", None)
                                                      ],
                                                     order="create_date asc")

        for inv in invoices_p:

            invoice_supplier = {
                "invoice_no": inv.sequence_number,
                "hash": (inv.hash[0] + inv.hash[11] + inv.hash[21] + inv.hash[31]) if len(inv.hash) >= 32 else "0",
                "source_id": inv.user_id.id,
                "period": int(str(inv.invoice_date)[5:7]),
                "invoice_date": inv.invoice_date,
                "invoice_type": "ND" if inv.move_type == "in_refund" else "FT",
                "supplier_id": inv.partner_id.ref or inv.partner_id.id,
                "document_totals": {
                    "tax_payable": utils.gross_total(inv.amount_tax),
                    "tax_payables": utils.gross_total(inv.amount_untaxed * 0.065),
                    "net_total_w": utils.gross_total(inv.amount_untaxed) - utils.gross_total(
                        inv.amount_untaxed * 0.065),
                    "net_total": utils.gross_total(inv.amount_untaxed),
                    # TODO: we must review this with invoice in different currency
                    "gross_total": utils.gross_total(inv.amount_total),
                    "deductible": {
                        "tax_base": utils.gross_total(inv.amount_untaxed),
                        # TODO: we must review this with invoice in different currency
                        "deductible_tax": "",
                        "deductible_percentage": "",
                        # "Currency": {
                        # "CurrencyCode": inv.currency_id.name,
                        #  "CurrencyAmount": utils.gross_total(inv.amount_total),
                        #  } if inv.currency_id != inv.company_id.currency_id else {},

                    },
                    "payments": [{
                        "payment_mechanism": payment.payment_mechanism or "TB",
                        "payment_amount": utils.gross_total(payment.amount),
                        "date": payment.date,
                    } for payment in inv.payment_ids]

                },
                "withholding_tax": [{
                    "withholding_tax_type": tax.tax_id.saft_wth_type,
                    "withholding_tax_description": tax.tax_id.name,
                    "withholding_tax_amount": utils.gross_total(tax.amount),
                } for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")]
            }
            if not invoice_supplier['document_totals']['payments']:
                invoice_supplier['document_totals'].pop('payments')

            # if inv.currency_id == inv.company_id.currency_id:
            # invoice_supplier["DocumentTotals"].pop("Currency")

            result["purchase_invoices"]["invoices_p"].append(invoice_supplier)
            result["purchase_invoices"]["number_of_entries"] += 1
        values.update(result)

    @api.model
    def _fill_saft_report_tax_table_values(self, options, values):
        result = {"tax_table": []}
        control = []

        for tax in self.env['account.tax'].search([('active', '=', True)]):
            if tax.saft_tax_type not in control:
                tax_table = {
                    'tax_type': tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS', 'IS'] else "IVA",
                    'tax_country_region': 'AO',
                    # 'tax_code':tax.tax_type if tax.tax_code == 'NS' else tax.tax_code,
                    'tax_code': tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS', 'IS'] else tax.code,
                    'description': tax.description,
                    'tax_percentage': tax.amount if tax.amount_type in ["percent",
                                                                        "division"] else "0",
                }

                control.append(tax.saft_tax_type)
                result['tax_table'].append(tax_table)
        values.update(result)
        
    @api.model
    def taxes_used(self):
        used_taxes = self.env['account.move.line'].search([
            ('tax_ids', '!=', False)
            ]).mapped('tax_ids')

        control = []
        result = {'tax_table': []}

        for tax in used_taxes:
            if tax.saft_tax_type not in control:
                if tax.saft_tax_code in ['IVA'] and tax.amount == 0:
                    tax_table = {
                        'TaxTableEntry':{
                        'TaxType': "IVA",
                        'TaxCountryRegion': 'AO',
                        'TaxCode': 'IVA',
                        'Description': 'Iva regime normal',
                        'TaxPercentage': "0.00",   
                        }
                    }

                elif tax.saft_tax_code in ['NS'] and tax.amount == 0:
                    tax_table = {
                        'TaxTableEntry':{
                        'TaxType': "IVA",
                        'TaxCountryRegion': 'AO',
                        'TaxCode': 'NS',
                        'Description': 'Não Sujeito',
                        'TaxPercentage': '0.00',
                        }
                    }

                elif tax.saft_tax_code in ['IS'] and tax.amount == 0:
                    tax_table = {
                        'TaxTableEntry':{
                        'TaxType': "IVA",
                        'TaxCountryRegion': 'AO',
                        'TaxCode': 'IS',
                        'Description': 'Isento',
                        'TaxPercentage': '0.00',
                        }
                    }

                else:
                    tax_table = {
                        'TaxTableEntry':{
                        'TaxType': tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS', 'IS'] else "IVA",
                        'TaxCountryRegion': 'AO',
                        'TaxCode': tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS', 'IS'] else tax.code,
                        'Description': tax.description,
                        'TaxPercentage': tax.amount if tax.amount_type in ["percent", "division"] else "0",}
                    }

                control.append(tax.saft_tax_type)
                result['tax_table'].append(tax_table)

        return result
        # result = {"tax_table": []}
        # control = []

        # for tax in self.env['account.tax'].search([('active', '=', True)]):
        #     if tax.saft_tax_type not in control:
        #         if tax.saft_tax_code in ['IVA'] and tax.amount==0:
        #             tax_table = {
        #             'tax_type': "IVA",
        #             'tax_country_region': 'AO',
        #             # 'tax_code':tax.tax_type if tax.tax_code == 'NS' else tax.tax_code,
        #             'tax_code': 'IVA',
        #             'description': 'Iva regime normal',
        #             'tax_percentage': "0.00",
        #         }
                    
        #         elif tax.saft_tax_code in ['NS'] and tax.amount==0:   
        #             tax_table = {
        #                 'tax_type': "IVA",
        #                 'tax_country_region': 'AO',
        #                 # 'tax_code':tax.tax_type if tax.tax_code == 'NS' else tax.tax_code,
        #                 'tax_code': 'NS',
        #                 'description': 'Não Sujeito',
        #                 'tax_percentage': '0.00',
        #             }
                    
                     
        #         elif tax.saft_tax_code in ['IS'] and tax.amount==0:   
        #             tax_table = {
        #                 'tax_type': "IVA",
        #                 'tax_country_region': 'AO',
        #                 # 'tax_code':tax.tax_type if tax.tax_code == 'NS' else tax.tax_code,
        #                 'tax_code': 'IS',
        #                 'description': 'Isento',
        #                 'tax_percentage': '0.00',
        #             }
                    
        #         else: tax_table = {
        #                 'tax_type': tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS', 'IS'] else "IVA",
        #                 'tax_country_region': 'AO',
        #                 # 'tax_code':tax.tax_type if tax.tax_code == 'NS' else tax.tax_code,
        #                 'tax_code': tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS', 'IS'] else tax.code,
        #                 'description': tax.description,
        #                 'tax_percentage': tax.amount if tax.amount_type in ["percent",
        #                                                                     "division"] else "0",
        #             }

        #         control.append(tax.saft_tax_type)
        #         result['tax_table'].append(tax_table)
        # return result

    @api.model
    def _prepare_saft_report_values(self, options):
        def format_float(amount, digits=2):
            return float_repr(amount or 0.0, precision_digits=digits)

        def format_date(date_str, formatter):
            date_obj = fields.Date.to_date(date_str)
            return date_obj.strftime(formatter)

        company = self.env.company

        if not company.company_registry:
            raise UserError(
                _("Please define `Company Registry` for your company."))

        template_values = {
            'company': company,
            'fiscal_year': company.accounting_year.name,
            'tax_entity': company.tax_entity,
            'xmlns': '',
            'file_version': 'undefined',
            'accounting_basis': 'undefined',
            'today_str': fields.Date.to_string(fields.Date.context_today(self)),
            'software_version': release.version,
            'date_from': options['date']['date_from'],
            'date_to': options['date']['date_to'],
            'format_float': format_float,
            'format_date': format_date,
        }

        self._fill_saft_report_general_ledger_values(options, template_values)
        self._fill_saft_report_products_values(options, template_values)
        self._fill_saft_report_tax_table_values(options, template_values)
        self._fill_saft_report_partner_ledger_values(options, template_values)
        self._fill_saft_report_sales_order_values(options, template_values)
        self._fill_saft_report_payments_values(options, template_values)

        return template_values

    @staticmethod
    def fun_label(x):
        if x not in ["TaxTable"]:
            return x[:-1]
        return "item"

    def create_saf_t_ao(self, value):
        saf_t_file = self.env["saf_t.ao"].create(value)
        action = self.env.ref('l10n_ao_saft.act_open_saf_t_ao').read()[0]
        action['views'] = [(self.env.ref('l10n_ao_saft.view_saf_t_ao_form').id, 'form')]
        action['res_id'] = saf_t_file.id
        return action

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be lower than End Date')

    def check_tax_entity(self, file_type):
        if file_type != 'I':
            return self.company_id.tax_entity or 'Global'
        return "Sede"

    def generate__xml_file(self):
        header = {
            "AuditFileVersion": self.company_id.audit_file_version,
            "CompanyID": self.company_id.company_registry,
            "TaxRegistrationNumber": self.company_id.vat,
            "TaxAccountingBasis": self.type,
            "CompanyName": self.company_id.name,
            "BusinessName": self.company_id.partner_id.industry_id.name or self.company_id.name,
            "CompanyAddress": {
                "BuildingNumber": "N/A",
                "StreetName": self.company_id.partner_id.street,
                "AddressDetail": self.company_id.partner_id.contact_address,
                "City": self.company_id.partner_id.city or 'Luanda',
                #"PostalCode": self.company_id.partner_id.zip,
                "Province": self.company_id.partner_id.state_id.name,
                "Country": self.company_id.partner_id.country_id.code
            },
            "FiscalYear": datetime.strptime(str(fields.Date.today()), '%Y-%m-%d').year,
            "StartDate": self.start_date,
            "EndDate": self.end_date,
            "CurrencyCode": self.company_id.currency_id.name,
            "DateCreated": (fields.Date.today()),
            "TaxEntity": self.check_tax_entity(self.type),
            "ProductCompanyTaxID": self.company_id.product_company_tax_id,
            "SoftwareValidationNumber": self.company_id.agt_cert_number or "447/AGT/2023",
            "ProductID": "Compllexus_Odoo/COMPLLEXUS - SMART- SOLUÇOES E SISTEMAS, LDA",
            "ProductVersion": 18.0,
            "HeaderComment": self.comment,
            "Telephone": self.company_id.phone,
            "Email": self.company_id.email,
            "Website": self.company_id.website,
        }

        file_type_dict = {
            "Header": header,
            "MasterFiles": "",
        }

        master_files = {
        }
        partners = self.env["res.partner"].browse()
        taxes = self.env["account.tax"]
        journals = self.env["account.journal"]
        products = self.env["product.product"]
        invoices = []
        if self.type == 'F':
            invoices = self.env["account.move"].search(
                [("invoice_date", ">=", self.start_date),
                 ("invoice_date", "<=", self.end_date),
                 ("company_id", "=", self.company_id.id),
                 ('state', '=', 'posted'),
                 ('move_type', 'in', ['out_invoice', 'out_refund'])
                 ,("system_entry_date", "!=", None)], order="create_date asc")

        if self.type=='A':
            invoices = self.env["account.move"].search(
                [("invoice_date", ">=", self.start_date),
                 ("invoice_date", "<=", self.end_date),
                 ("company_id", "=", self.company_id.id),
                 ('state', '=', 'posted'),
                 ('move_type', 'in', ['in_invoice', 'in_refund'])
                 ,("system_entry_date", "!=", None)], order="create_date asc")


        partners |= invoices.mapped("partner_id.commercial_partner_id")
        products |= invoices.mapped("invoice_line_ids.product_id")
        taxes |= invoices.mapped("invoice_line_ids.tax_ids")
        saf_t_data = partners.get_content_saf_t_ao(self.start_date, self.end_date, self.company_id)
        partners = self.env["res.partner"].browse(invoices.mapped("partner_id.commercial_partner_id").ids)
        saf_t_data = partners.get_content_saf_t_ao(self.start_date, self.end_date, self.company_id)

        
        
        if self.type == 'F':
            if saf_t_data.get("Customer"):
                master_files["Customers"] = saf_t_data["Customer"]
            file_type_dict["SourceDocuments"] = {
                    "SalesInvoices": invoices.get_content_saf_t_ao(self.start_date, self.end_date, self.company_id).get(
                        "SalesInvoices")}
        elif self.type == 'A':
            if saf_t_data.get("Supplier"):
                master_files["Suppliers"] = saf_t_data["Supplier"]
            file_type_dict["SourceDocuments"] = {
                    "PurchaseInvoices": invoices.get_content_supplier_saf_t_ao(self.start_date, self.end_date, self.company_id).get(
                        "SalesInvoices")}

        if invoices:
            master_files["Products"] = products.get_content_saf_t_ao(invoices).get("Product")
        # if taxes.get_content_saf_t_ao().get("TaxTable"):
        #         master_files["TaxTable"] = taxes.get_content_saf_t_ao().get("TaxTable")
        
        master_files["TaxTable"] = self.taxes_used()["tax_table"]

        file_type_dict["MasterFiles"] = master_files
        content_xml_obj = dicttoxml(file_type_dict, custom_root="AuditFile",
                                     item_func=lambda x: self.fun_label(x),
                                     attr_type=False)
        dom = parseString(content_xml_obj)
        return self.create_saf_t_ao({
            "text": utils.prepare_xml(content_xml_obj),
            "audit_file_version": self.company_id.audit_file_version,
            "file_type": self.type,
            "company_id": self.company_id.id,
            "fiscal_year": '2025',
            "start_date": self.start_date,
            "end_date": self.end_date,
            "product_company_tax_id": self.company_id.product_company_tax_id,
            "software_validation_number":"447/AGT/2023" or self.company_id.software_validation_number,
            "product_id": "Compllexus_Odoo",
            "Product_version": self.company_id.product_version,
            "header_comment": self.comment,
            "user_id": self.env.user.id,
        })

# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from . import utils
from datetime import date

import requests
from datetime import datetime
from odoo.tools import float_is_zero, float_compare, pycompat
from odoo.tools.misc import formatLang
from collections import OrderedDict
from odoo.exceptions import UserError
import json
# import hmac
# import hashlib
# import base64


class SAFTAccountMove(models.Model):
    _inherit = 'account.move'

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

    hash = fields.Char(string="Key", default="0")
    has_with_problem = fields.Char(string='Key', default='0')
    hash_control = fields.Char(string="Key Version", relate='company_id.key_version')
    system_entry_date = fields.Datetime("Signature Datetime")
    settlement_discount = fields.Char(string="Settlement Discount")
    settlement_amount = fields.Float(string="Settlement Amount")
    settlement_date = fields.Date(string="Settlement Date")
    sequence_int = fields.Char('Sequence int')
    sequence_saft_invoice = fields.Char()
    transaction_type = fields.Selection(string="Tipo de Lançamento",
                                        required=True,
                                        selection=[('N', 'Normal'),
                                                   ('R', 'Regularizações'),
                                                   ('A', 'Apur. Resultados'),
                                                   ('J', 'Ajustamentos')],
                                        help="Categorias para classificar os movimentos contabilísticos ao exportar o SAFT",
                                        default="N", )
    tax_line_ids = fields.Many2one('account.tax', string='tax_line')

    #Estado da Factura eletrónica
    invoice_status = fields.Selection([
        ('not_sent', 'Não Enviado'),
        ('sent', 'Enviado'),
        ('accepted', 'Aceite'),
        ('rejected', 'Rejeitado'),
        ('not_validated', 'Não Validado'),
    ], string='Estado e-Invoice', default='not_sent')

    def get_content_saf_t_ao(self, start_date, end_date, company):
        result = {
            "SalesInvoices": {
                "NumberOfEntries": 0,
                "TotalDebit": 0,
                "TotalCredit": 0,
                "Invoices": [],
            },
            "Invoices": {
                "NumberOfEntries": 0,
                "Invoices": [],
            },
        }
        # Sales Invoicing
        invoices = self.search([("invoice_date", ">=", start_date),
                                ("invoice_date", "<=", end_date),
                                ("company_id", "=", company.id),
                                ('state', '=', 'posted'),
                                #("payment_state", "in", ['paid', 'not_paid', 'partial']),
                                ("system_entry_date", "!=", None),
                                ('move_type', 'in', ['out_invoice', 'out_refund'])], order="create_date asc")
        for inv in invoices:
            status_code = 'N'
            if inv.state == 'cancel':
                status_code = 'A'
            elif inv.journal_id.self_billing is True:
                status_code = 'S'
            source_billing = "P"

            # FACTURAS CLIENTES

            if inv.move_type in ["out_invoice", "out_refund"]:
                invoice_customer = {
                    "InvoiceNo": inv.name,
                    "DocumentStatus": {
                        "InvoiceStatus": status_code,
                        "InvoiceStatusDate": str(inv.system_entry_date).replace(' ',
                                                                                'T') if inv.system_entry_date else str(
                            inv.create_date).replace(
                            ' ', 'T'),
                        # "Reason": "",  # TODO GENERATE CONTENT FOR REASON
                        "SourceID": inv.user_id.id,
                        "SourceBilling": source_billing,
                    },
                    "Hash": inv.hash,
                    "HashControl": "447/AGT/2023" + "." + inv.hash_control,
                    "Period": int(str(inv.invoice_date)[5:7]),
                    "InvoiceDate": inv.invoice_date,
                    "InvoiceType": "FT" if inv.move_type == "out_invoice" else "NC",
                    "SpecialRegimes": {
                        "SelfBillingIndicator": 1 if inv.journal_id.self_billing else 0,
                        "CashVATSchemeIndicator": 1 if inv.company_id.tax_exigibility else 0,
                        "ThirdPartiesBillingIndicator": 0,
                    },
                    "SourceID": inv.user_id.id,
                    # "EACCode": "N/A",
                    "SystemEntryDate": str(inv.system_entry_date).replace(' ',
                                                                          'T') if inv.system_entry_date else str(
                        inv.create_date).replace(
                        ' ', 'T'),
                    "TransactionID": "%s %s %s" % (
                        inv.invoice_date, inv.journal_id.code.replace(' ', ''),
                        inv.name.replace(' ', '').replace('/', '')) if inv.name else '',
                    "CustomerID": inv.partner_id.id,
                    # "ShipTo": "",  # TODO: 4.1.4.15
                    # "ShipFrom": "",  # TODO: 4.1.4.16
                    # "MovementEndTime": "",  # TODO: 4.1.4.17,
                    "MovementStartTime": str(inv.system_entry_date).replace(' ',
                                                                            'T') if inv.system_entry_date else str(
                        inv.create_date).replace(
                        ' ', 'T'),  # TODO: 4.1.4.18,
                    "Lines": [],
                    "DocumentTotals": {
                        "TaxPayable": utils.gross_total(inv.amount_tax),
                        "NetTotal": utils.gross_total(inv.amount_untaxed),
                        # TODO: we must review this with invoice in different currency
                        "GrossTotal": utils.gross_total(inv.amount_total),
                        # TODO: we must review this with invoice in different currency
                        "Currency": {
                            "CurrencyCode": inv.currency_id.name,
                            "CurrencyAmount": utils.gross_total(inv.amount_total),
                            "ExchangeRate": inv.currency_id.rate,
                        } if inv.currency_id != inv.company_id.currency_id else {},
                        "Settlement": {
                            "SettlementDiscount": utils.gross_total(inv.settlement_discount or 0),
                            "SettlementAmount": utils.gross_total(inv.settlement_amount or 0),
                            # "SettlementDate": inv.settlement_date or "",
                            "PaymentTerms": inv.payment_ids.name if inv.payment_ids.name else "",
                        },
                        "Payments": [{
                            "PaymentMechanism": payment.payment_mechanism or "TB",
                            "PaymentAmount": utils.gross_total(payment.amount),
                            #"PaymentDate": payment.payment_date,
                        } for payment in inv.payment_ids]

                    },
                    "WithholdingTax": [{
                        "WithholdingTaxType": tax.tax_id.saft_wth_type,
                        "WithholdingTaxDescription": tax.tax_id.name,
                        "WithholdingTaxAmount": utils.gross_total(tax.amount),
                    } for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")],
                }
                if not invoice_customer['DocumentTotals']['Payments']:
                    invoice_customer['DocumentTotals'].pop('Payments')

                # payments = []
                # for payment in inv.payment_ids:
                #     payment_values = {
                #         "PaymentMechanism": payment.payment_mechanism,
                #         "PaymentAmount": utils.gross_total(payment.amount),
                #         "PaymentDate": payment.payment_date,
                #     }
                #     payments.append(payment_values)
                # invoice_customer['DocumentTotals']['Payment'] = payments

                for line in inv.invoice_line_ids:
                    lines = OrderedDict()
                    lines["LineNumber"] = line.id
                    lines["ProductCode"] = line.product_id.id if line.product_id else 'HS12D'
                    lines["ProductDescription"] = utils.remove_special_chars(
                        line.product_id.description_sale or line.product_id.name
                    )[:199]
                    lines["Quantity"] = line.quantity
                    lines["UnitOfMeasure"] = line.product_id.uom_id.name
                    lines["UnitPrice"] = utils.gross_total(line.price_subtotal / line.quantity) if line.quantity else 0.00
                    lines["TaxPointDate"] = inv.invoice_date

                    # 🔑 Coloca References aqui, logo após TaxPointDate
                    if inv.move_type == "out_refund":
                        # Extrair texto depois da vírgula, se existir
                        reason = inv.ref or ""
                        if "," in reason:
                            reason = reason.split(",", 1)[1].strip()
                        else:
                            reason = reason.strip()

                        # Garantir no máximo 50 caracteres
                        reason = utils.remove_special_chars(reason)[:50] or "Cancelamento de factura"

                        lines["References"] = {
                            "Reference": inv.ref_invoice,
                            "Reason": reason,
                        }

                    lines["Description"] = utils.remove_special_chars(
                        line.product_id.name[:199]) if line.product_id.name else "-"
                    lines["CreditAmount" if inv.move_type == "out_invoice" else "DebitAmount"] = utils.gross_total(line.price_subtotal)

                    if inv.move_type == "out_refund" and inv.state in ["open", "paid"]:
                        lines["DebitAmount"] = utils.gross_total(line.price_subtotal)

                    if inv.move_type == "out_invoice" and inv.state in ["open", "paid"]:
                        lines["CreditAmount"] = utils.gross_total(line.price_subtotal)

                    lines["Tax"] = []
                    taxes_to_use = self.check_saft_tax(
                        line.tax_ids, line.tax_ids.mapped('tax_on'))
                    if taxes_to_use:
                        for tax in taxes_to_use:
                            if tax.tax_on != 'withholding':
                                tax_values = {
                                    "TaxType": tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS', 'IS'] else "IVA",
                                    "TaxCountryRegion": tax.country_region,  # FIXME: 4.1.4.19.15.2.
                                    "TaxCode": tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS',
                                                                                       'IS'] else tax.saft_tax_code,
                                }
                                if tax.amount_type in ["percent", "division"]:
                                    tax_values["TaxPercentage"] = utils.gross_total(tax.amount)
                                elif tax.amount_type in ["fixed"]:
                                    tax_values["TaxAmount"] = utils.gross_total(tax.amount)
                                if tax.tax_on == "invoice":
                                    if tax.amount == 0:
                                        lines["TaxExemptionReason"] = tax.exemption_reason
                                        lines["TaxExemptionCode"] = tax.name #"M21"
                                lines["Tax"].append(tax_values)
                    if not lines["Tax"]:
                        lines["Tax"].append({"TaxType": "NS",
                                             "TaxCountryRegion": "AO",
                                             "TaxCode": "NS",
                                             "TaxPercentage": "0.00"})
                        lines["TaxExemptionReason"] = line.tax_ids.exemption_reason #"Isento nos termos da alínea l) do nº1 do artigo 12.º do CIVA"
                        lines["TaxExemptionCode"] = line.tax_ids.name #"M21"
                    lines["SettlementAmount"] = utils.gross_total(line.discount)
                    # lines["CustomsInformation"] = {  # TODO: 4.1.4.19.19.
                    #     "ARCNo": "",
                    #     "IECAmount": "",
                    # }
                    invoice_customer["Lines"].append(lines)

                if inv.currency_id == inv.company_id.currency_id:
                    invoice_customer["DocumentTotals"].pop("Currency")

                if not [tax.id for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")]:
                    invoice_customer.pop("WithholdingTax")

                result["SalesInvoices"]["Invoices"].append(invoice_customer)
                #Updating ==========

                if inv.move_type == "out_refund" and inv.payment_state in ["not_paid", "paid","partial","reversed"]:
                    result["SalesInvoices"]["TotalDebit"] += utils.gross_total(
                        inv.amount_untaxed)
                elif inv.move_type == "out_invoice" and inv.payment_state in ["not_paid", "paid","partial","reversed"]:
                    result["SalesInvoices"]["TotalCredit"] += utils.gross_total(
                        inv.amount_untaxed)

                # if inv.move_type == "out_refund":
                #     result["SalesInvoices"]["TotalDebit"] += utils.gross_total(inv.amount_untaxed)
                #
                # elif inv.move_type == "out_invoice" and inv.state in ["open", "paid"]:  # if is normal or invoiced
                #     result["SalesInvoices"]["TotalCredit"] += utils.gross_total(inv.amount_untaxed)

                if status_code not in ['A', 'F']:
                    result["SalesInvoices"]["NumberOfEntries"] += 1


                # invoice_supplier = {
                #     "InvoiceNo": inv.number,
                #     "SourceID": inv.user_id.id,
                #     "Period": int(inv.date_invoice[5:7]),
                #     "InvoiceDate": inv.date_invoice,
                #     "InvoiceType": "ND" if inv.move_type == "in_refund" else "FT",
                #     "SupplierID": inv.partner_id.ref or inv.partner_id.id,
                #     "DocumentTotals": {
                #         "TaxPayable": utils.gross_total(inv.amount_tax),
                #         "NetTotal": utils.gross_total(inv.amount_untaxed),
                #         # TODO: we must review this with invoice in different currency
                #         "GrossTotal": utils.gross_total(inv.amount_total),
                #         "Deductible": {
                #             "TaxBase": utils.gross_total(inv.amount_untaxed),
                #             # TODO: we must review this with invoice in different currency
                #             "DeductibleTax": "",
                #             "DeductiblePercentage": "",
                #             # "Currency": {
                #             # "CurrencyCode": inv.currency_id.name,
                #             #  "CurrencyAmount": utils.gross_total(inv.amount_total),
                #             #  } if inv.currency_id != inv.company_id.currency_id else {},

                #         },
                #         "Payments": [{
                #             "PaymentMechanism": payment.payment_mechanism or "TB",
                #             "PaymentAmount": utils.gross_total(payment.amount),
                #             "PaymentDate": payment.payment_date,
                #         } for payment in inv.payment_ids]

                #     },
                #     "WithholdingTax": [{
                #         "WithholdingTaxType": tax.tax_id.saft_wth_type,
                #         "WithholdingTaxDescription": tax.tax_id.name,
                #         "WithholdingTaxAmount": utils.gross_total(tax.amount),
                #     } for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")]

                # }
                # if not invoice_supplier['DocumentTotals']['Payments']:
                #     invoice_supplier['DocumentTotals'].pop('Payments')

                # # if inv.currency_id == inv.company_id.currency_id:
                # # invoice_supplier["DocumentTotals"].pop("Currency")

                # result["Invoices"]["Invoices"].append(invoice_supplier)
                # result["Invoices"]["NumberOfEntries"] += 1
        return result

    def get_content_supplier_saf_t_ao(self, start_date, end_date, company):

        result = {
            "SalesInvoices": {
                "NumberOfEntries": 0,
                "TotalDebit": 0,
                "TotalCredit": 0,
                "Invoices": [],
            },
            "Invoices": {
                "NumberOfEntries": 0,
                "Invoices": [],
            },

            # Codigo Acrescentado
            "PurchaseInvoices": {
                "NumberOfEntries": 0,
            }
        }
        # Sales Invoicing
        invoices = self.search([("invoice_date", ">=", start_date),
                                ("invoice_date", "<=", end_date),
                                ("company_id", "=", company.id),
                                ('state', '=', 'posted'),
                                ("system_entry_date", "!=", None),
                                ('move_type', 'in', ['in_invoice', 'in_refund'])], order="create_date asc")
        for inv in invoices:
            print("INVOICE", inv.name, inv.move_type, inv.state, inv.journal_id.self_billing)
            status_code = 'N'
            if inv.state == 'cancel':
                status_code = 'A'
            elif inv.journal_id.self_billing is True:
                status_code = 'S'
            source_billing = "P"

            # FACTURAS Fornecedores

            if inv.move_type in ["in_invoice", "in_refund"]:
                invoice_customer = {
                    "InvoiceNo": inv.name,
                    "DocumentStatus": {
                        "InvoiceStatus": status_code,
                        "InvoiceStatusDate": str(inv.system_entry_date).replace(' ',
                                                                                'T') if inv.system_entry_date else str(
                            inv.create_date).replace(
                            ' ', 'T'),
                        "SourceID": inv.user_id.id,
                        "SourceBilling": source_billing,
                    },
                    "Hash": inv.hash,
                    "HashControl": "447/AGT/2023" + "." + inv.hash_control,
                    "Period": int(str(inv.invoice_date)[5:7]),
                    "InvoiceDate": inv.invoice_date,
                    "InvoiceType": "FT" if inv.move_type == "in_invoice" else "NC",
                    "SpecialRegimes": {
                        "SelfBillingIndicator": 1 if inv.journal_id.self_billing else 0,
                        "CashVATSchemeIndicator": 1 if inv.company_id.tax_exigibility else 0,
                        "ThirdPartiesBillingIndicator": 0,
                    },
                    "SourceID": inv.user_id.id,
                    "SystemEntryDate": str(inv.system_entry_date).replace(' ',
                                                                          'T') if inv.system_entry_date else str(
                        inv.create_date).replace(
                        ' ', 'T'),
                    "TransactionID": "%s %s %s" % (
                        inv.invoice_date, inv.journal_id.code.replace(' ', ''),
                        inv.name.replace(' ', '').replace('/', '')) if inv.name else '',
                    "SupplierID": inv.partner_id.id,
                    "MovementStartTime": str(inv.system_entry_date).replace(' ',
                                                                            'T') if inv.system_entry_date else str(
                        inv.create_date).replace(
                        ' ', 'T'),  # TODO: 4.1.4.18,
                    "Lines": [],
                    "DocumentTotals": {
                        "TaxPayable": utils.gross_total(inv.amount_tax),
                        "NetTotal": utils.gross_total(inv.amount_untaxed),
                        "GrossTotal": utils.gross_total(inv.amount_total),
                        "Currency": {
                            "CurrencyCode": inv.currency_id.name,
                            "CurrencyAmount": utils.gross_total(inv.amount_total),
                            "ExchangeRate": inv.currency_id.rate,
                        } if inv.currency_id != inv.company_id.currency_id else {},
                        "Settlement": {
                            "SettlementDiscount": utils.gross_total(inv.settlement_discount or 0),
                            "SettlementAmount": utils.gross_total(inv.settlement_amount or 0),
                            "PaymentTerms": inv.payment_ids.name if inv.payment_ids.name else "",
                        },
                        "Payments": [{
                            "PaymentMechanism": payment.payment_mechanism or "TB",
                            "PaymentAmount": utils.gross_total(payment.amount),
                        } for payment in inv.payment_ids]

                    },
                    "WithholdingTax": [{
                        "WithholdingTaxType": tax.tax_id.saft_wth_type,
                        "WithholdingTaxDescription": tax.tax_id.name,
                        "WithholdingTaxAmount": utils.gross_total(tax.amount),
                    } for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")],
                }
                if not invoice_customer['DocumentTotals']['Payments']:
                    invoice_customer['DocumentTotals'].pop('Payments')

                for line in inv.invoice_line_ids:
                    lines = {
                        "LineNumber": line.id,
                        "ProductCode": line.product_id.id if line.product_id else 'HS12D',
                        "ProductDescription": line.product_id.description_sale or line.product_id.name,
                        "Quantity": line.quantity,
                        "UnitOfMeasure": line.product_id.uom_id.name,
                        "UnitPrice": utils.gross_total(line.price_subtotal/line.quantity) if line.quantity else 0.00,
                        # "TaxBase": utils.gross_total(line.price_subtotal) if line.price_unit == 0.0 else 0.00,
                        "TaxPointDate": inv.invoice_date,
                        "Description": utils.remove_special_chars(line.product_id.name)[:200] if line.product_id.name else "-",
                        "CreditAmount" if inv.move_type == "in_invoice" else "DebitAmount": utils.gross_total(line.price_subtotal),

                    }

                    if inv.move_type == "in_refund":
                        lines['References'] = {
                            "Reference": inv.ref_invoice,
                            # "Reason": inv.name,
                        }

                    if inv.move_type == "in_refund" and inv.state in ["open", "paid"]:
                        lines["DebitAmount"] = utils.gross_total(line.price_subtotal)

                    if inv.move_type == "out_invoice" and inv.state in ["open", "paid"]:
                        lines["CreditAmount"] = utils.gross_total(line.price_subtotal)

                    lines["Tax"] = []
                    taxes_to_use = self.check_saft_tax(
                        line.tax_ids, line.tax_ids.mapped('tax_on'))
                    if taxes_to_use:
                        for tax in taxes_to_use:
                            if tax.tax_on != 'withholding':
                                tax_values = {
                                    "TaxType": tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS', 'IS'] else "IVA",
                                    "TaxCountryRegion": tax.country_region,  # FIXME: 4.1.4.19.15.2.
                                    "TaxCode": tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS',
                                                                                       'IS'] else tax.saft_tax_code,
                                }
                                if tax.amount_type in ["percent", "division"]:
                                    tax_values["TaxPercentage"] = utils.gross_total(tax.amount)
                                elif tax.amount_type in ["fixed"]:
                                    tax_values["TaxAmount"] = utils.gross_total(tax.amount)
                                if tax.tax_on == "invoice":
                                    if tax.amount == 0:
                                        lines["TaxExemptionReason"] = tax.exemption_reason
                                        lines["TaxExemptionCode"] = tax.name #"M21"
                                lines["Tax"].append(tax_values)
                    if not lines["Tax"]:
                        lines["Tax"].append({"TaxType": "NS",
                                             "TaxCountryRegion": "AO",
                                             "TaxCode": "NS",
                                             "TaxPercentage": "0.00"})
                        lines["TaxExemptionReason"] = line.tax_ids.exemption_reason #"Isento nos termos da alínea l) do nº1 do artigo 12.º do CIVA"
                        lines["TaxExemptionCode"] = line.tax_ids.name #"M21"
                    lines["SettlementAmount"] = utils.gross_total(line.discount)

                    invoice_customer["Lines"].append(lines)

                if inv.currency_id == inv.company_id.currency_id:
                    invoice_customer["DocumentTotals"].pop("Currency")

                if not [tax.id for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")]:
                    invoice_customer.pop("WithholdingTax")

                result["SalesInvoices"]["Invoices"].append(invoice_customer)

                if inv.move_type == "in_refund" and inv.payment_state in ["not_paid", "paid","partial","reversed"]:
                    result["SalesInvoices"]["TotalDebit"] += utils.gross_total(
                        inv.amount_untaxed)
                elif inv.move_type == "out_invoice" and inv.payment_state in ["not_paid", "paid","partial","reversed"]:
                    result["SalesInvoices"]["TotalCredit"] += utils.gross_total(
                        inv.amount_untaxed)

                if status_code not in ['A', 'F']:
                    result["SalesInvoices"]["NumberOfEntries"] += 1


        ####################################################################
        # result = {
        #     "PurchaseInvoices": {
        #         "NumberOfEntries": 0,
        #         "TotalDebit": 0,
        #         "TotalCredit": 0,
        #         "Invoices": [],
        #     },
        #     "Invoices": {
        #         "NumberOfEntries": 0,
        #         "Invoices": [],
        #     },

        # }
        # # Supplier Invoicing
        # invoices = self.search([("invoice_date", ">=", start_date),
        #                         ("invoice_date", "<=", end_date),
        #                         ("company_id", "=", company.id),
        #                         ('state', '=', 'posted'),
        #                         ("system_entry_date", "!=", None),
        #                         ('move_type', 'in', ['in_invoice', 'in_refund'])], order="create_date asc")
        # for inv in invoices:
        #     status_code = 'N'
        #     if inv.state == 'cancel':
        #         status_code = 'A'
        #     elif inv.journal_id.self_billing is True:
        #         status_code = 'S'
        #     source_billing = "P"


        #     if inv.move_type in ["in_invoice", "in_refund"]:
        #         invoice_supplier = {
        #             "InvoiceNo": inv.name,
        #             "DocumentStatus": {
        #                 "InvoiceStatus": status_code,
        #                 "InvoiceStatusDate": str(inv.system_entry_date).replace(' ',
        #                                                                         'T') if inv.system_entry_date else str(
        #                     inv.create_date).replace(
        #                     ' ', 'T'),
        #                 # "Reason": "",  # TODO GENERATE CONTENT FOR REASON
        #                 "SourceID": inv.user_id.id,
        #                 "SourceBilling": source_billing,
        #             },
        #             "Hash": inv.hash,
        #             "HashControl": inv.hash_control,
        #             "Period": int(str(inv.invoice_date)[5:7]),
        #             "InvoiceDate": inv.invoice_date,
        #             "InvoiceType": "FT" if inv.move_type == "in_invoice" else "NC",
        #             "SpecialRegimes": {
        #                 "SelfBillingIndicator": 1 if inv.journal_id.self_billing else 0,
        #                 "CashVATSchemeIndicator": 1 if inv.company_id.tax_exigibility else 0,
        #                 "ThirdPartiesBillingIndicator": 0,
        #             },
        #             "SourceID": inv.user_id.id,
        #             # "EACCode": "N/A",
        #             "SystemEntryDate": str(inv.system_entry_date).replace(' ',
        #                                                                   'T') if inv.system_entry_date else str(
        #                 inv.create_date).replace(
        #                 ' ', 'T'),
        #             "TransactionID": "%s %s %s" % (
        #                 inv.invoice_date, inv.journal_id.code.replace(' ', ''),
        #                 inv.name.replace(' ', '').replace('/', '')) if inv.name else '',
        #             "SupplierID": inv.partner_id.id,
        #             # "ShipTo": "",  # TODO: 4.1.4.15
        #             # "ShipFrom": "",  # TODO: 4.1.4.16
        #             # "MovementEndTime": "",  # TODO: 4.1.4.17,
        #             "MovementStartTime": str(inv.system_entry_date).replace(' ',
        #                                                                     'T') if inv.system_entry_date else str(
        #                 inv.create_date).replace(
        #                 ' ', 'T'),  # TODO: 4.1.4.18,
        #             "Lines": [],
        #             "DocumentTotals": {
        #                 "TaxPayable": utils.gross_total(inv.amount_tax),
        #                 "NetTotal": utils.gross_total(inv.amount_untaxed),
        #                 # TODO: we must review this with invoice in different currency
        #                 "GrossTotal": utils.gross_total(inv.amount_total),
        #                 # TODO: we must review this with invoice in different currency
        #                 "Currency": {
        #                     "CurrencyCode": inv.currency_id.name,
        #                     "CurrencyAmount": utils.gross_total(inv.amount_total),
        #                     "ExchangeRate": inv.currency_id.rate,
        #                 } if inv.currency_id != inv.company_id.currency_id else {},
        #                 "Settlement": {
        #                     "SettlementDiscount": inv.settlement_discount or 0,
        #                     "SettlementAmount": inv.settlement_amount or 0,
        #                     # "SettlementDate": inv.settlement_date or "",
        #                     "PaymentTerms": inv.payment_ids.name if inv.payment_ids.name else "",
        #                 },
        #                 "Payments": [{
        #                     "PaymentMechanism": payment.payment_mechanism or "TB",
        #                     "PaymentAmount": utils.gross_total(payment.amount),
        #                     #"PaymentDate": payment.payment_date,
        #                 } for payment in inv.payment_ids]

        #             },
        #             "WithholdingTax": [{
        #                 "WithholdingTaxType": tax.tax_id.saft_wth_type,
        #                 "WithholdingTaxDescription": tax.tax_id.name,
        #                 "WithholdingTaxAmount": utils.gross_total(tax.amount),
        #             } for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")],
        #         }
        #         if not invoice_supplier['DocumentTotals']['Payments']:
        #             invoice_supplier['DocumentTotals'].pop('Payments')

        #         for line in inv.invoice_line_ids:
        #             lines = {
        #                 "LineNumber": line.id,
        #                 "ProductCode": line.product_id.id if line.product_id else 'HS12D',
        #                 "ProductDescription": line.product_id.description_sale or line.product_id.name,
        #                 "Quantity": line.quantity,
        #                 "UnitOfMeasure": line.product_id.uom_id.name,
        #                 "UnitPrice": line.price_unit,
        #                 "TaxBase": line.price_subtotal ifutils.gross_total( line.price_unit ==) 0.0 else 0.0,
        #                 "TaxPointDate": inv.invoice_date,
        #                 "Description": line.product_id.name[:200] if line.product_id.name else "-",
        #                 "CreditAmount" if inv.move_type == "in_invoice" else "CreditAmount": line.price_subtotal,

        #             }

        #             if inv.move_type == "in_refund":
        #                 lines['References'] = {
        #                     "Reference": inv.ref_invoice,
        #                     # "Reason": inv.name,
        #                 }


        #             if inv.move_type == "in_refund" and inv.state in ["open", "paid"]:
        #                 lines["CreditAmount"] = utils.gross_total(line.price_subtotal)

        #             if inv.move_type == "in_invoice" and inv.state in ["open", "paid"]:
        #                 lines["DebitAmount"] = utils.gross_total(line.price_subtotal)

        #             lines["Tax"] = []
        #             taxes_to_use = self.check_saft_tax(
        #                 line.tax_ids, line.tax_ids.mapped('tax_on'))
        #             if taxes_to_use:
        #                 for tax in taxes_to_use:
        #                     if tax.tax_on != 'withholding':
        #                         tax_values = {
        #                             "TaxType": tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS', 'IS'] else "IVA",
        #                             "TaxCountryRegion": tax.country_region,  # FIXME: 4.1.4.19.15.2.
        #                             "TaxCode": tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS',
        #                                                                                'IS'] else tax.saft_tax_code,
        #                         }
        #                         if tax.amount_type in ["percent", "division"]:
        #                             tax_values["TaxPercentage"] = utils.gross_total(tax.amount)
        #                         elif tax.amount_type in ["fixed"]:
        #                             tax_values["TaxAmount"] = utils.gross_total(tax.amount)
        #                         if tax.tax_on == "invoice":
        #                             if tax.amount == 0:
        #                                 lines["TaxExemptionReason"] = tax.exemption_reason
        #                                 lines["TaxExemptionCode"] = "M21"
        #                         lines["Tax"].append(tax_values)
        #             if not lines["Tax"]:
        #                 lines["Tax"].append({"TaxType": "NS",
        #                                      "TaxCountryRegion": "AO",
        #                                      "TaxCode": "NS",
        #                                      "TaxPercentage": "0.00"})
        #                 lines["TaxExemptionReason"] = "Isento nos termos da alínea l) do nº1 do artigo 12.º do CIVA"
        #                 lines["TaxExemptionCode"] = "M21"
        #             lines["SettlementAmount"] = line.discount

        #             invoice_supplier["Lines"].append(lines)

        #         if inv.currency_id == inv.company_id.currency_id:
        #             invoice_supplier["DocumentTotals"].pop("Currency")

        #         if not [tax.id for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")]:
        #             invoice_supplier.pop("WithholdingTax")

        #         result["PurchaseInvoices"]["Invoices"].append(invoice_supplier)

        #         if inv.move_type == "in_refund" and inv.payment_state in ["not_paid", "paid","partial","reversed"]:
        #             result["PurchaseInvoices"]["TotalCredit"] += utils.gross_total(
        #                 inv.amount_untaxed)
        #         elif inv.move_type == "in_invoice" and inv.payment_state in ["not_paid", "paid","partial","reversed"]:
        #             result["PurchaseInvoices"]["TotalDebit"] += utils.gross_total(
        #                 inv.amount_untaxed)

        #         result["PurchaseInvoices"]["NumberOfEntries"] += 1

        return result

    def sign_old_credit_notes(self):
        start_date = date(2022, 1, 1)
        end_date = date(2022, 12, 31)
        for company in self.env['res.company'].search([]):
            last_signed = False
            domain = [('move_type', '=', 'out_refund'), ('state', 'in', ['open', 'paid']),
                      ("date_invoice", ">=", start_date), ("date_invoice", "<=", end_date)]
            if self.env.user.has_group('base.group_multi_company'):
                domain.append(('company_id', '=', company.id))
            invoices = self.env['account.move'].search(
                domain, order='sequence_int asc')
            n = 1
            for invoice in invoices:
                invoice.system_entry_date = invoice.create_date
                sequence_int = invoice.number.replace('NC C', '').replace('NC F', '').split('/')
                invoice.sequence_int = sequence_int[-1]
                invoice.hash_control = invoice.company_id.key_version
                total = utils.gross_total(invoice.amount_total)
                if not last_signed:
                    domain = [('move_type', '=', invoice.move_type), ('state', 'in', ['open', 'paid']),
                              ("date_invoice", "<", start_date)]
                    if self.env.user.has_group('base.group_multi_company'):
                        domain.append(('company_id', '=', company.id))
                    _last_invoices = self.env['account.move'].search(
                        domain, order='sequence_int asc')
                    last_invoice_hash = ""
                    content_hash = ""
                    if _last_invoices:
                        last_invoice_hash = _last_invoices[-1].hash
                        content = (
                            invoice.date_invoice, str(invoice.system_entry_date).replace(' ', 'T'), invoice.name,
                            str(total),
                            last_invoice_hash)
                        content_hash = ";".join(content)
                    else:
                        content = (
                            invoice.date_invoice, str(invoice.system_entry_date).replace(' ', 'T'), invoice.name,
                            str(total))
                        content_hash = ";".join(content) + ';'
                else:
                    last_invoice_hash = last_signed[-1].hash
                    content = (
                        invoice.date_invoice, str(invoice.system_entry_date).replace(' ', 'T'), invoice.name,
                        str(total),
                        last_invoice_hash)
                    content_hash = ";".join(content)
                last_signed = invoice
                # content_hash = invoice.get_content_to_sign()
                print(content_hash)

                content_signed = utils.signer(content_hash)
                if not content_signed:
                    raise ValidationError(_("Problema ao assinar a factura"))
                print(content_signed)
                invoice.hash = content_signed

    def action_invoice_open(self):
        self.system_entry_date = fields.Datetime.now()
        self._prepare_cost_center()
        self.tax_repeated(self.tax_line_ids)
        result = super(SAFTAccountMove, self).action_invoice_open()
        if self.state == "open":
            self.hash_control = self.company_id.key_version
            content_hash = self.get_content_to_sign()
            sequence_int = self.inv_no.replace('FT C', '').replace('FT F', '').split('/')
            self.sequence_int = sequence_int[-1]
            print('**************** here in sequence it', sequence_int)
            print(content_hash)
            content_signed = utils.signer(content_hash)
            if not content_signed:
                raise ValidationError(_("Problema ao assinar a factura"))
            self.hash = content_signed
        return result

    def get_customer_id(self, customer):
        if not customer.vat:
            final_consumer = self.env['res.partner'].search([('vat', '=', '999999999')])
            if final_consumer:
                customer = final_consumer[0]
        final_consumer = self.env['res.partner'].search([('ref', '=', 'CF')])
        if final_consumer:
            customer = final_consumer[0]
        return customer.ref

    def sign_old_invoices(self):
        start_date = date(2022, 1, 1)
        end_date = date(2022, 12, 31)
        last_signed = False
        for company in self.env['res.company'].search([]):
            domain = [('move_type', '=', 'out_invoice'), ('state', 'in', ['open', 'paid']),
                      ("date_invoice", ">=", start_date), ('company_id', '=', company.id),
                      ("date_invoice", "<=", end_date)]
            if self.env.user.has_group('base.group_multi_company'):
                domain.append(('company_id', '=', company.id))
            invoices = self.env['account.move'].search(
                domain, order='sequence_int asc')
            n = 1
            for invoice in invoices:
                print('************************* ', invoice)
                invoice.system_entry_date = invoice.create_date
                print('************************* %d / %d reference %s' % (n, len(invoices), invoice.number))
                n = n + 1
                invoice.tax_repeated(invoice.tax_line_ids)
                invoice.hash_control = invoice.company_id.key_version
                total = utils.gross_total(invoice.amount_total)
                if not last_signed:
                    _last_invoices = self.env['account.move'].search(
                        [('move_type', '=', invoice.move_type), ('state', 'in', ['open', 'paid']),
                         ("date_invoice", "<", start_date), ('company_id', '=', company.id)], order='sequence_int asc')
                    last_invoice_hash = ""
                    content_hash = ""
                    if _last_invoices:
                        last_invoice_hash = _last_invoices[-1].hash
                        content = (
                            invoice.date_invoice, str(invoice.system_entry_date).replace(' ', 'T'), invoice.name,
                            str(total),
                            last_invoice_hash)
                        content_hash = ";".join(content)
                    else:
                        content = (
                            invoice.date_invoice, str(invoice.system_entry_date).replace(' ', 'T'), invoice.name,
                            str(total))
                        content_hash = ";".join(content) + ';'
                else:
                    last_invoice_hash = last_signed[-1].hash
                    content = (
                        invoice.date_invoice, str(invoice.system_entry_date).replace(' ', 'T'), invoice.name,
                        str(total),
                        last_invoice_hash)
                    content_hash = ";".join(content)
                last_signed = invoice
                # content_hash = invoice.get_content_to_sign()
                print(content_hash)

                content_signed = utils.signer(content_hash)
                if not content_signed:
                    raise ValidationError(_("Problema ao assinar a factura"))
                print(content_signed)
                invoice.hash = content_signed

    def clean_numbers(self):
        start_date = date(2022, 1, 1)
        end_date = date(2022, 12, 31)
        last_signed = False
        invoices = self.env['account.move'].search(
            [('move_type', '=', 'out_invoice'), ('state', 'in', ['open', 'paid']),
             ("date_invoice", ">=", start_date), ("date_invoice", "<=", end_date)], order='date_invoice asc')
        n = 1
        # SEQUENCIA
        for invoice in invoices:
            ir_parameter = self.env['ir.config_parameter'].search([('key', '=', 'customer.invoice.sequence')])
            print('********** parameter *********** ', ir_parameter)
            if ir_parameter:
                number = int(ir_parameter.value)
                if invoice.move_type == 'out_invoice':
                    invoice.number = 'FT C2022/%0*d' % (3, number) or 'NC C2022/%0*d' % (3, number)
                    ir_parameter.value = number + 1

    def fill_sequence_int(self):
        for invoice in self.search([('state', '!=', 'draft')]):
            if invoice.number:
                sequence_int = invoice.number.replace('FT C', '').replace('FT F', '').split('/')
                invoice.sequence_int = sequence_int[-1]

    # @api.constrains('invoice_date')
    # def _check_data_invoice(self):
    #     if self.move_type in ['out_invoice', 'out_refund']:
    #         invoices = self.env['account.move'].search(
    #             [('move_type', 'in', ['out_invoice', 'out_refund']), ('company_id', '=', self.company_id.id),
    #              ('invoice_date', '>', self.invoice_date),
    #              ('state', 'in', ['draft', 'posted'])],
    #             order="invoice_date")
    #         if invoices:
    #             raise ValidationError(_(
    #                 "There is already approved invoices whose date is higher than the one that is being inserted,"
    #                 " you can not insert invoices, whose date is smaller than these"))

    def renumber_invoices(self):
        start_date = date(2022, 1, 1)
        end_date = date(2022, 12, 31)
        print('renumber invoices *********** ')
        for company in self.env['res.company'].search([]):
            last_signed = False
            domain = [('move_type', '=', 'out_invoice'), ('state', 'in', ['open', 'paid']),
                      ("date_invoice", ">=", start_date), ("date_invoice", "<=", end_date)]
            if self.env.user.has_group('base.group_multi_company'):
                domain.append(('company_id', '=', company.id))
            invoices = self.env['account.move'].search(
                domain, order='date_invoice asc')
            n = 1
            for invoice in invoices:
                domain = [('code', '=', 'renumber.customer.invoice.sequence')]
                if self.env.user.has_group('base.group_multi_company'):
                    domain.append(('company_id', '=', company.id))
                sequence = self.env['ir.sequence'].search(domain)
                if sequence:
                    print(sequence.prefix, sequence.number_next_actual, company.name)
                    invoice.number = "%s%0*d" % (sequence.prefix, 4, sequence.number_next_actual)
                    print(invoice, invoice.inv_no, invoice.number)
                    sequence.number_next_actual = sequence.number_next_actual + 1

    def get_content_to_sign(self):
        print("entrou aqui ....................")
        domain = [
            ('state', 'in', ['posted']),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
        ]
        if self.env.user.has_group('base.group_multi_company'):
            domain.append(('company_id', '=', self.company_id.id))
        _last_invoices = self.env['account.move'].search(domain, order='create_date asc').filtered(
            lambda r: r.invoice_date.strftime("%Y") == self.invoice_date.strftime("%Y"))

        if _last_invoices:
            if len(_last_invoices) > 1:
                last_account_move = _last_invoices[-2]
                if last_account_move:
                    total = utils.gross_total(self.amount_total)

                    content = (str(self.invoice_date), str(self.system_entry_date).replace(
                        ' ', 'T'), self.name, str(total), last_account_move.hash)
                    return ";".join(content)
                    print("mostra =============",content)
            elif len(_last_invoices) == 1:
                total = utils.gross_total(self.amount_total)
                content = (
                    str(self.invoice_date), str(self.system_entry_date).replace(' ', 'T'), self.name,
                    str(total))
                return ";".join(content) + ';'


    def _build_einvoice_payload(self):
        """Constrói o JSON requerido pela AGT a partir da fatura (account.move).
        Usa o schema que nos foi entregue.
        """
        self.ensure_one()
        invoice = self

        invoice_list_item = {
            'invoice': {
                'invoiceNo': invoice.name or invoice.invoice_number if hasattr(invoice, 'invoice_number') else invoice.name,
                'invoiceStatus': 'N',  # ajustar conforme lógica da empresa
                'invoiceData': invoice.invoice_date.isoformat() if invoice.invoice_date else datetime.utcnow().date().isoformat(),
                'invoiceType': 'FT' if invoice.move_type == 'out_invoice' else 'NC',
                'EACCode': invoice.journal_id.code or '00000',
                'systemEntryDate': (invoice.create_date or datetime.utcnow()).isoformat(),
                'customerTaxID': invoice.partner_id.vat or '',
                'companyName': invoice.partner_id.name or '',
                'lineList': [],
                'documentTotals': {
                    'taxPayable': float(invoice.amount_tax),
                    'netTotal': float(invoice.amount_untaxed),
                    'grossTotal': float(invoice.amount_total),
                    'currency': {
                        'currencyCode': invoice.currency_id.name or 'AOA',
                        'currencyAmount': float(invoice.amount_total),
                        'exchangeRate': 1.0,
                    }
                }
            }
        }

        line_no = 1
        for line in invoice.invoice_line_ids:
            line_item = {
                'lineNo': line_no,
                'productCode': line.product_id.default_code or str(line.id),
                'productDescription': line.name,
                'quantity': float(line.quantity),
                'unitOfMeasure': line.product_uom_id.name if line.product_uom_id else '',
                'unitPrice': float(line.price_unit),
                'debitAmount': 0.0,
                'creditAmount': float(line.price_subtotal) if line.price_subtotal >= 0 else 0.0,
                'tax': {},
                'taxVATExemptionCode': '',
                'settlementAmount': float(line.discount or 0.00),
            }
            # Preencher informação de impostos se existir
            if line.tax_ids:
                tax = line.tax_ids[0]
                line_item['tax'] = {
                    'taxType': 'IVA' if 'iva' in (tax.name or '').lower() else 'NS',
                    'taxCountryRegion': invoice.company_id.country_id.code or 'AO',
                    'taxCode': tax.name,
                    'taxPercentage': float(tax.amount),
                    'taxAmount': float(line.price_total - line.price_subtotal),
                }

            invoice_list_item['invoice']['lineList'].append(line_item)
            line_no += 1

        payload = {
            'salesInvoices': {
                'numberOfEntries': 1,
                'invoiceList': [invoice_list_item]
            }
        }
        return payload

    def action_send_einvoice_to_agt(self):
        """Acção para construir payload e enviar para o endpoint de testes da AGT.
        """

        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()

        agt_url = params.get_param('l10n_ao_einvoice.agt_test_url') or False
        if not agt_url:
            raise UserError('Parametro l10n_ao_einvoice.agt_test_url não definido (ir.config_parameter).')

        # Ler parâmetros de cabeçalho conforme sua especificação
        token = params.get_param('l10n_ao_einvoice.token') or ''
        signature_param = params.get_param('l10n_ao_einvoice.signature') or ''
        creation_date_param = params.get_param('l10n_ao_einvoice.creationDate') or ''
        product_version = params.get_param('l10n_ao_einvoice.productVersion') or ''
        secret_key = params.get_param('l10n_ao_einvoice.secretKey') or ''

        # Garantir creationDate em ISO8601 (ex.: 2025-09-18T12:34:56Z) — se não existir, gera agora
        if creation_date_param:
            creation_date = creation_date_param
        else:
            # gerar em UTC ISO format com 'Z'
            creation_date = (datetime.utcnow().replace(microsecond=0).isoformat() + 'Z')

        # Construir payload JSON
        payload = self._build_einvoice_payload()
        payload_json = json.dumps(payload, ensure_ascii=False)

        print('Payload JSON a enviar:', payload_json)
 
        signature = signature_param

        # Validacões simples de comprimento conforme a tabela (por exemplo)
        if token and len(token) > 500:
            raise UserError('token excede maxlength 500')
        if product_version and len(product_version) > 20:
            raise UserError('productVersion excede maxlength 20')
        if secret_key and len(secret_key) > 1024:
            raise UserError('secretKey excede maxlength 1024')

        # Montar headers de acordo com a especificação
        headers = {
            'Content-Type': 'application/json',
            'token': token,
            'taxRegistrationNumber': self.company_id.vat or '',
            'signature': signature or '',
            'creationDate': creation_date,
            'softwareValidationNo': self.company_id.agt_cert_number or "447/AGT/2023",
            'productID': "Compllexus_Odoo/COMPLLEXUS - SMART- SOLUÇOES E SISTEMAS, LDA",
            'productVersion': "17.0",
            # Nota: secretKey NÃO deve ser enviado em headers ao serviço; é usado apenas localmente para gerar signature.
        }

        # Se existirem credentials adicionais (ex.: Bearer token), mantemos compatibilidade
        agt_token = params.get_param('l10n_ao_einvoice.agt_token')
        if agt_token:
            headers['Authorization'] = f'Bearer {agt_token}'

        try:
            #response = requests.post(agt_url, data=payload_json.encode('utf-8'), headers=headers, timeout=30)
            #self.einvoice_response = response.text or str(response.content)
            if True: #response.status_code in (200, 201):
                self.invoice_status = 'sent'
            else:
                self.invoice_status = 'not_sent'
                raise UserError(f'Json da Fatura não aceite pela AGT: {response.text}')
            return #response.status_code, response.text
        except Exception as e:
            #self.einvoice_response = str(e)
            self.invoice_status = 'not_sent'
            raise UserError(f'Erro ao enviar e-fatura para AGT: {str(e)}')

        """{"salesInvoices": {"numberOfEntries": 1, "invoiceList":
         [{"invoice": 
         {"invoiceNo": "FT C2025/4", "invoiceStatus": "N", "invoiceData": "2025-08-14", 
         "invoiceType": "FT", "EACCode": "FT C", "systemEntryDate": "2025-08-14T10:53:21.808568",
          "customerTaxID": "999999999999999", "companyName": "Consumidor Final", 
          "lineList": [{"lineNo": 1, "productCode": "214", "productDescription": "Service on Timesheets",
           "quantity": 1.0, "unitOfMeasure": "Horas", "unitPrice": 200000.0, 
           "debitAmount": 0.0, "creditAmount": 200000.0, 
           "tax": {"taxType": "IVA", "taxCountryRegion": "AO", "taxCode": "IVA 0%", "taxPercentage": 0.0, "taxAmount": 0.0}, 
           "taxVATExemptionCode": "", "settlementAmount": 200000.0}], 
           "documentTotals": {"taxPayable": 0.0, "netTotal": 200000.0, "grossTotal": 200000.0, "currency": {"currencyCode": "AOA", "currencyAmount": 200000.0, "exchangeRate": 1.0}}}}]}}
        """

    def action_consult_einvoice_to_agt(self):
        """Acção para consultar o estado da e-fatura na AGT.
        """

        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()

        agt_consult_url = params.get_param('l10n_ao_einvoice.agt_consult_url') or False
        if not agt_consult_url:
            raise UserError('Parametro l10n_ao_einvoice.agt_consult_url não definido (ir.config_parameter).')

        # Ler parâmetros de cabeçalho conforme sua especificação
        token = params.get_param('l10n_ao_einvoice.token') or ''
        signature_param = params.get_param('l10n_ao_einvoice.signature') or ''
        creation_date_param = params.get_param('l10n_ao_einvoice.creationDate') or ''
        product_version = params.get_param('l10n_ao_einvoice.productVersion') or ''
        secret_key = params.get_param('l10n_ao_einvoice.secretKey') or ''

        # Garantir creationDate em ISO8601 (ex.: 2025-09-18T12:34:56Z) — se não existir, gera agora
        if creation_date_param:
            creation_date = creation_date_param
        else:
            # gerar em UTC ISO format com 'Z'
            creation_date = (datetime.utcnow().replace(microsecond=0).isoformat() + 'Z')

        signature = signature_param

        # Validacões simples de comprimento conforme a tabela (por exemplo)
        if token and len(token) > 500:
            raise UserError('token excede maxlength 500')
        if product_version and len(product_version) > 20:
            raise UserError('productVersion excede maxlength 20')
        if secret_key and len(secret_key) > 1024:
            raise UserError('secretKey excede maxlength 1024')

        # Montar headers de acordo com a especificação
        headers = {
            'Content-Type': 'application/json',
            'token': token,
            'taxRegistrationNumber': self.company_id.vat or '',
            'signature': signature or '',
            'creationDate': creation_date,
            'softwareValidationNo': self.company_id.agt_cert_number or "447/AGT/2023",
            'productID': "Compllexus_Odoo/COMPLLEXUS - SMART- SOLUÇOES E SISTEMAS, LDA",
            'productVersion': "17.0",
            # Nota: secretKey NÃO deve ser enviado em headers ao serviço; é usado apenas localmente para gerar signature.
        }
        # Se existirem credentials adicionais (ex.: Bearer token), mantemos compatibilidade
        agt_token = params.get_param('l10n_ao_einvoice.agt_token')
        if agt_token:
            headers['Authorization'] = f'Bearer {agt_token}'
        try:
            #consult_url = f"{agt_consult_url}/{self.company_id.vat or ''}/{self.name or ''}"
            #response = requests.get(consult_url, headers=headers, timeout=30)
            #self.einvoice_response = response.text or str(response.content)
            if True: #response.status_code in (200, 201):
                self.invoice_status = 'accepted'
            else:
                self.invoice_status = 'not_validated'
                raise UserError(f'Consulta não validada pela AGT: {response.text}')
            return #response.status_code, response.text
        except Exception as e:
            #self.einvoice_response = str(e)
            self.invoice_status = 'rejected'
            raise UserError(f'Erro ao consultar e-fatura na AGT: {str(e)}')
    
    def action_avoid(self):
        pass     
           
    def action_post(self):
        result = super(SAFTAccountMove, self).action_post()

        for move in self:
            if move.move_type in ['out_invoice', 'out_refund']:
                move.system_entry_date = fields.Datetime.now()

                # Preenche o hash e hash_control
                if move.state == "posted":
                    move.hash_control = move.company_id.key_version
                    content_hash = move.get_content_to_sign()
                    sequence_int = move.name.replace('FT C', '').replace('FT F', '').split('/')
                    move.sequence_int = sequence_int[-1]
                    content_signed = utils.signer(content_hash)
                    if not content_signed:
                        raise ValidationError(_("Problem Signing Invoice"))
                    move.hash = content_signed

                # Define a referência da fatura original, se for nota de crédito
                if move.move_type == 'out_refund' and move.reversed_entry_id:
                    move.ref_invoice = move.reversed_entry_id.name

        return result
    # def action_post(self):
    #     print("SOU FACTURA...")
    #     result = super(SAFTAccountMove, self).action_post()
    #     if self.move_type in ['out_invoice', 'out_refund']:
    #         self.system_entry_date = fields.Datetime.now()
    #         if self.state == "posted":
    #             self.hash_control = self.company_id.key_version
    #             content_hash = self.get_content_to_sign()
    #             print(content_hash)
    #             sequence_int = self.name.replace('FT C', '').replace('FT F', '').split('/')
    #             self.sequence_int = sequence_int[-1]
    #             content_signed = utils.signer(content_hash)
    #             if not content_signed:
    #                 raise ValidationError(_("Problem Signing Invoice"))
    #             self.hash = content_signed
    #             print(self.hash)
    #     return result

    def get_content_sign_saft(self, date_start, date_end):
        domain = [
            ('state', 'in', ['posted', ]),
            ('move_type', 'in', ['out_invoice']), ('invoice_date', '>=', date_start), ('invoice_date', '<=', date_end)
        ]
        if self.env.user.has_group('base.group_multi_company'):
            domain.append(('company_id', '=', self.company_id.id))
        invoices = self.search(domain, order='create_date asc')
        for j, rec in enumerate(invoices):
            if j == 0:
                total = utils.gross_total(rec.amount_total)
                content = (
                    str(rec.invoice_date), str((rec.create_date).strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T'),
                    str(rec.sequence_saft_invoice),
                    str(total))
                print('ME mostra **********************', content)
                has_with_problem = ";".join(content) + ";"
                print(has_with_problem)
                hash = utils.signer(has_with_problem)
                print(has_with_problem)
                rec.has_with_problem = hash
            else:
                total = utils.gross_total(rec.amount_total)
                content = (
                    str(rec.invoice_date), str((rec.create_date).strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T'),
                    rec.sequence_saft_invoice,
                    str(total), invoices[j].has_with_problem)
                has_with_problem = ";".join(content)
                print(has_with_problem)
                has_with_problem = utils.signer(has_with_problem)
                rec.has_with_problem = has_with_problem

    def clean_number_invoices(self, date_start, date_end):
        domain = [('state', 'in', ['posted', ]), ('move_type', 'in', ['out_invoice']),
                  ('invoice_date', '>=', date_start), ('invoice_date', '<=', date_end)]
        invoices = self.search(domain, order='invoice_date asc')
        for rec in invoices:
            ir_paramenter = self.env['ir.config_parameter'].sudo().get_param('cp.satf.sequence.invoice')
            account_payment = self.env['account.payment'].search([("ref", '=', rec.name)], order='date desc')
            print(ir_paramenter)
            if ir_paramenter:
                number = int(ir_paramenter)
                rec.sequence_saft_invoice = "FT C" + str(date_start).split('-')[0] + "/" + '%0*d' % (
                    3, number)
                for payment in account_payment:
                    payment.sequence_saft_rf = "RG " + str(date_start).split('-')[
                        0] + "/" + '%0*d' % (
                                                   3, number)
                    print("RG " + str(date_start).split('-')[
                        0] + "/" + '%0*d' % (
                              3, number))
                    break
                self.env['ir.config_parameter'].sudo().set_param('cp.satf.sequence.invoice', number + 1)

        for rec in invoices:
            rec.get_content_sign_saft(date_start, date_end)
            break

        for rec in invoices:
            print(rec.sequence_saft_invoice, rec.hash)
            
class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    @api.constrains('reason')
    def _check_reason_length(self):
        for rec in self:
            if rec.reason and len(rec.reason) > 50:
                raise ValidationError(
                    "O campo 'Motivo' não pode ter mais de 50 caracteres."
                )
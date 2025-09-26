from odoo import models, fields, api, _
from . import utils
from datetime import datetime

mechanisms = [('CD', 'Cartão débito'),
              ('CC', 'Cartão crédito'),
              ('MB', 'Referências de pagamento para Multicaixa'),
              ('NU', 'Numerário'),
              ('CI', 'Crédito documentário internacional'),
              ('CO', 'Cheque ou cartão oferta'),
              ('CS', 'Compensação de saldos em conta corrente'),
              ('DE', 'Dinheiro electrónico,por exemplo residente em cartões de fidelidade ou de pontos'),
              ('OU', 'Outros meios aqui não assilados'),
              ('PR', 'Permuta de bens'),
              ('TB', 'Transferência bancária')]


class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_mechanism = fields.Selection(string="Payment Mechanism", selection=mechanisms)

    _sql_constraints = [('unique_reference', 'UNIQUE(payment_reference)',
                         '  de referência do pagamento deve ser único!')]

    payment_state = fields.Selection(related='move_id.payment_state')
    invoice_date = fields.Date(related='move_id.invoice_date')
    sequence_saft_rf = fields.Char()

    def get_content_saf_t_ao(self):

        result = {
            'Payments': {
                "NumberOfEntries": 0,
                "TotalDebit": 0,
                "TotalCredit": 0,
                "Payments": [],
            }
        }

        payments = self.filtered(lambda r: r.state in ['sent', 'posted', 'reconciled', 'cancelled'])
        for payment in payments:
            payment_status = 'N'
            if payment.state == 'cancelled':
                payment_status = 'A'
            line = payment.mapped("line_ids")
            payment_data = {
                "PaymentRefNo": payment.receipt_no,
                "Period": str(payment.date)[5:7],
                "TransactionID": "%s %s %s" % (
                    payment.date, payment.journal_id.code.replace(' ', ''),
                    payment.name.replace('/', '').replace(' ', '')),
                "TransactionDate": payment.date,
                "PaymentType": 'RG',
                "Description": 'P ' + str(payment.amount_text),  # payment.amount_text + ' '
                "SystemID": payment.name,
                "DocumentStatus": {
                    "PaymentStatus": payment_status,
                    "PaymentStatusDate": str(payment.write_date).replace(' ', 'T'),
                    # "Reason": "",
                    "SourceID": payment.create_uid.id,
                    "SourcePayment": 'P',
                },
                "PaymentMethod": {
                    "PaymentMechanism": payment.payment_mechanism or 'TB',
                    "PaymentAmount": utils.gross_total(payment.amount),
                    "PaymentDate": payment.date,
                },
                "SourceID": payment.create_uid.id,
                "SystemEntryDate": str(payment.create_date).replace(' ', 'T'),
                "CustomerID": payment.partner_id.ref or payment.partner_id.id,
            }
            for inv in payment.line_ids:
                withholding_tax = []

                for line in inv.move_id:
                    payment_data["Line"] = {
                        "LineNumber": line.id,
                        "SourceDocumentID": {
                            "OriginatingON": line.name,
                            "InvoiceDate": line.invoice_date,
                            "Description": line.name,
                        },
                        "SettlementAmount": sum(line.invoice_line_ids.mapped("discount")),
                    }
                    if line.move_type == "out_refund" and line.state in ["open", "paid"]:
                        payment_data["Line"]["DebitAmount"] = line.amount_untaxed
                    elif line.move_type == "out_invoice" and line.state in ["open", "paid"]:
                        payment_data["Line"]["CreditAmount"] = line.amount_untaxed

                    payment_data["Line"]["Tax"] = [{
                        "TaxType": tax.saft_tax_type,
                        "TaxCountryRegion": tax.country_region,  # FIXME: 4.1.4.19.15.2.
                        "TaxCode": tax.saft_tax_code,
                        "TaxPercentage": tax.amount if tax.amount_type in ["percent", "division"] else 0.0,
                        "TaxAmount": tax.amount if tax.amount_type in ["fixed"] else "",
                    } for tax in line.invoice_line_ids.tax_ids if tax.tax_on == "invoice"]
                    for tax in line.invoice_line_ids.tax_ids:
                        if tax.tax_on == "invoice":
                            if tax.amount == 0:
                                payment_data['Line']["TaxExemptionReason"] = tax.exemption_reason
                                payment_data['Line']["TaxExemptionCode"] = tax.saft_tax_code

                payment_data["DocumentTotals"] = {
                    "TaxPayable": utils.gross_total(line.amount_tax),
                    "NetTotal": utils.gross_total(line.amount_untaxed),
                    "GrossTotal": utils.gross_total(line.amount_total),
                    "Settlement": {
                        "SettlementAmount": 0.0,
                    },
                }

                if inv.currency_id != inv.company_id.currency_id:
                    payment_data["DocumentTotals"]["Currency"] = {
                        "CurrencyCode": inv.currency_id.name,
                        "CurrencyAmount": inv.amount_total,
                        "ExchangeRate": inv.currency_id.rate
                    }

                for tax in line.invoice_line_ids.tax_ids.filtered(lambda l: l.tax_id.tax_on == "withholding"):
                    withholding_tax.append({
                        "WithholdingTaxType": tax.tax_id.saft_wth_type,
                        "WithholdingTaxDescription": tax.tax_id.name,
                        "WithholdingTaxAmount": tax.amount,
                    })

                if withholding_tax:
                    payment_data["WithholdingTax"] = withholding_tax

                if line.move_type == "out_refund" and line.state in ["open", "paid"]:
                    result["Payments"]["TotalDebit"] += line.amount_untaxed
                elif line.move_type == "out_invoice" and line.state in ["open", "paid"]:
                    result["Payments"]["TotalCredit"] += line.amount_untaxed

            result['Payments']['Payments'].append(payment_data)
        result['Payments']['NumberOfEntries'] = len(payments)

        return result

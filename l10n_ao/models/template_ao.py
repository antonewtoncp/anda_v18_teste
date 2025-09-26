from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"
    _description = "Adiciona os prefixos padrão as contas"

    @template("ao")
    def _get_ao_template_data(self):
        return {
            "code_digits": "1",
            "use_anglo_saxon": True,
            "property_account_receivable_id": "l10n_ao.account_chart_31121",
            "property_account_payable_id": "l10n_ao.account_chart_32121",
            "property_account_income_categ_id": "l10n_ao.account_chart_6211",
            "property_account_expense_categ_id": "l10n_ao.account_chart_75239",
            "property_account_expense_id": "l10n_ao.account_chart_75239",
            "property_stock_account_input_categ_id": "l10n_ao.account_chart_2121",
            "property_stock_account_output_categ_id": "l10n_ao.account_chart_7131",
            "property_stock_valuation_account_id": "l10n_ao.account_chart_2631",
            "property_account_income_id": "l10n_ao.account_chart_6211",
            "property_account_income_credit_id": "l10n_ao.account_chart_3194",
            "property_account_expense_credit_id": "l10n_ao.account_chart_68124",
            "tax_cash_basis_account_id": "l10n_ao.account_chart_3422",
            "income_currency_exchange_account_id": "l10n_ao.account_chart_6621",
            "expense_currency_exchange_account_id": "l10n_ao.account_chart_7621",
        }

    @template("ao", "res.company")
    def _get_ao_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.ao",
                "bank_account_code_prefix": "43",
                "cash_account_code_prefix": "48",
                "transfer_account_code_prefix": "11",
                "account_default_pos_receivable_account_id": "l10n_ao.account_chart_311211",
                "income_currency_exchange_account_id": "l10n_ao.account_chart_id454",
                "expense_currency_exchange_account_id": "l10n_ao.account_chart_7621",
                "account_journal_early_pay_discount_loss_account_id": "l10n_ao.account_chart_id474",
                "account_journal_early_pay_discount_gain_account_id": "l10n_ao.account_chart_id464",
                "default_cash_difference_income_account_id": "l10n_ao.account_chart_id465",
                "default_cash_difference_expense_account_id": "l10n_ao.account_chart_id465",
                "account_journal_suspense_account_id": "l10n_ao.account_chart_4821",
                "account_journal_payment_debit_account_id": "l10n_ao.account_chart_id4741",
                "account_journal_payment_credit_account_id": "l10n_ao.account_chart_id403",
                "control_account_nature": True,
                "automatic_partner_account": True,
                "account_sale_tax_id": "vat_14",
                "account_purchase_tax_id": "vat_14_purchase",
                "transfer_account_id": "l10n_ao.account_chart_id450",
                "group_fiscal_year": True
            },
        }

    @template("ao", "account.journal")
    def _get_ao_account_journal(self):
        return {
            "sale": {
                "name": "Faturas de Clientes",
                "type": "sale",
                "code": _("FT C"),
                "show_on_dashboard": True,
                "color": 11,
                "sequence": 5,
            },
            "purchase": {
                "name": "Faturas de Fornecedores",
                "type": "purchase",
                "code": _("FT F"),
                "show_on_dashboard": True,
                "color": 11,
                "sequence": 6,
            },
            "general": {
                "name": "Operações Diversas",
                "type": "general",
                "code": _("DIV"),
                "show_on_dashboard": True,
                "sequence": 7,
            },
            "exch": {
                "name": "Diferença de Câmbio",
                "type": "general",
                "code": _("CAMB"),
                "show_on_dashboard": False,
                "sequence": 9,
            },
            "caba": {
                "name": "Impostos em regime de caixa",
                "type": "general",
                "code": _("CABA"),
                "show_on_dashboard": False,
                "sequence": 10,
            },
            "bank": {
                "name": "Banco",
                "type": "bank",
                "show_on_dashboard": True,
            },
            "cash": {
                "name": "Numerário",
                "type": "cash",
                "show_on_dashboard": True,
            },
        }

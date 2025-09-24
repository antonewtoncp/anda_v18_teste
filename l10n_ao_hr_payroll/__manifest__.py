# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Angola Payroll",
    "category": "HR",
    "author": "Compllexus",
    "version": "15.1",
    "description": """
Angolan Payroll Rules.
======================
	* Categorias de Regras Salariais
	* Regras Salariais
    * Abonos
    * Deduções
    """,
    "data": [
        "data/sequence.xml",
        "data/delete_data.xml",
        "data/salary_structure_data.xml",
        "data/salary_rule_category_data.xml",
        "data/rules_deduction_data.xml",
        "data/rules_remuneration_data.xml",
        "data/holidays_data.xml",
        "data/base_inss_irt_data.xml",
        #"data/work_type_entry.xml",
    ],
    "depends": [
        "hr_payroll",
        "hr_holidays",
    ],
    "installable": True,
}

# -i l10n_ao_hr_payroll -d odooF -u l10n_ao_hr_payroll

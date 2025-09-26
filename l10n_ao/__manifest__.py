# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2023 Compllexus, Lda. All Rights Reserved
# http://compllexus.compllexus.com.
{
    "name": "Angola - Accounting",
    "icon": "/account/static/description/l10n.png",
    "countries": ["ao"],
    "version": "1.0",
    "author": "Compllexus",
    "category": "Accounting/Localizations/Account Charts",
    "sequence": 1,
    "summary": "PGC - Angola",
    "website": "https://compllexus.com",
    "description": "Planos de contas para Angola",
    "depends": [
        "base",
        "account",
        "base_vat",
        "account_accountant",
        "ao_localization",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_sequence.xml",
        "data/account_note_data.xml",
        "views/account_payment_view.xml",
        "views/account_config_settings.xml",
        "views/account_note_view.xml",
        "views/account_account_view.xml",
        "views/account_tax_view.xml",
        "views/account_move_view.xml",
        # "data/account_exemption_taxes.xml",
    ],
    "installable": True,
    "auto_install": False,
}

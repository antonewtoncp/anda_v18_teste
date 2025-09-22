# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2023 compllexus , Lda. All Rights Reserved
# https://compllexus.compllexus.com.
{
    "name": "Angola Localization",
    "version": "0.1",
    "category": "Localization",
    "description": """Bank,Provinces""",
    "author": "Compllexus",
    "summary": "Localization data for Angola",
    "website": "http://compllexus.com",
    "depends": ["base", "calendar"],
    "data": [
        "views/banks_view.xml",
        "views/res_partner_view.xml",
        "views/calendar_event_view.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": False,
}

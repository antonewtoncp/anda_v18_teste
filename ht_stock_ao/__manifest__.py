# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2023  Compllexus, Lda. All Rights Reserved
# https://compllexus.com
{
    "name": "Angola - Stock",
    "version": "0.1",
    "author": "Compllexus",
    "category": "Inventory/Inventory",
    "sequence": 1,
    "summary": "Stock and Logistics - Angola",
    "website": "https://compllexus.com",
    "description": "Angolan manage stock and logistics activities",
    "depends": [
        "stock",
        "stock_account",
        "ht_account_ao",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "wizards/article_extract_wizard.xml",
        "wizards/article_resume_wizard.xml",
        "wizards/categorize_article_wizard.xml",
        "views/stock_picking_view.xml",
        "views/category_view.xml",
        "views/product_template_view.xml",
        "views/res_company_view.xml",
        # 'views/res_config_view.xml',
        "reports/report.xml",
        "reports/report_stockpicking_operations_valued.xml",
        "reports/report_delivery_slip_ao.xml",
        "reports/report_transport_slip_ao.xml",
        "reports/article_extract_report.xml",
        "reports/article_resume_report .xml",
    ],
    "installable": True,
    "auto_install": False,
    "price": 120000,
    "license": "OPL-1",
    "currency": "AOA",
}

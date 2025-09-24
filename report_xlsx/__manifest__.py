# -*- coding: utf-8 -*-
{
    "name": "Base report xlsx",
    "summary": "Base module extension to generate xlsx report",
    "description": """
Base module extension to generate xlsx report
    """,
    "author": "TeamUp4Solutions, TaxDotCom",
    "website": "https://www.teamup4solutions.com",
    "category": "Customizations",
    "version": "18.0.0.0",
    "depends": ["base", "web"],
    "external_dependencies": {"python": ["xlsxwriter", "xlrd"]},
    "data": [
        # 'security/ir.model.access.csv',
    ],
    "demo": [],
    "assets": {
        "web.assets_backend": [
            "report_xlsx/static/src/js/report/action_manager_report.esm.js",
        ],
    },
}

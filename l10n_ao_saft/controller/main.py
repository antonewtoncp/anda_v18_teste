from odoo import http
from odoo.http import request


class SAFTAOController(http.Controller):
    @http.route("/report/xml/l10n_ao_saft.saft_report/<int:saft_id>", type="http", auth="public")
    def download(self, saft_id, **kwargs):
        result = request.env["saf_t.ao"].browse(saft_id)
        filename = f"saft_ao_{saft_id}.xml"
        header = [
            ("Content-Type", "application/xml"),
            ("Content-Disposition", f"attachment; filename={filename}"),
        ]
        return request.make_response(result.text, header)

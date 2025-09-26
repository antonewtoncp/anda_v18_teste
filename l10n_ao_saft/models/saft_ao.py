from odoo import models, fields, api, _

document_types = [
    ("I", "Contabilidade integrada com facturação"),
    ("C", "Contabilidade"),
    ("F", "Faturação"),
    ("P", "Faturação parcial"),
    ("R", "Recibos"),
    ("S", "Autofaturação"),
    ("A", "Aquisição de bens e serviços"),
    ("Q", "Aquisição de bens e serviços integrada com a faturação"),
]


class SafTAO(models.Model):
    _name = "saf_t.ao"
    _description = "Standard Audit File for Tax"

    name = fields.Char("Name", compute="_compute_name")
    start_date = fields.Date(string="Start Date", required=True, readonly=True)
    end_date = fields.Date(string=" End Date", required=True, readonly=True)
    user_id = fields.Many2one("res.users", string="User", readonly=True)
    company_id = fields.Many2one(
        "res.company", required=True, string="Company", readonly=True
    )
    data = fields.Binary("File", readonly=True)
    text = fields.Text(string="Text", readonly=True)
    audit_file_version = fields.Char(
        string="Audit File Version",
        size=10,
        required=True,
        readonly=True,
        help="Ficheiro de auditoria",
    )
    state = fields.Selection(
        [("new", "New"), ("approved", "Validated"), ("done", "AGT Submitted")],
        "State",
        default="new",
    )
    file_type = fields.Selection(
        string="File XML Type",
        selection=document_types,
        help="Tipos de Ficheiro SAF-T AO a ser exportado",
        required=True,
        readonly=True,
        default="I",
    )
    fiscal_year = fields.Integer(string="Fiscal Year", required=True, readonly=True)
    product_company_tax_id = fields.Char(
        string="NIF",
        size=20,
        required=True,
        readonly=True,
        help="Identidade Fiscal da Empresa Produtora do Software",
    )
    software_validation_number = fields.Char(
        string="Software Number",
        required=True,
        readonly=True,
        help="Número de validação atribuído à entidade produtora " "do software",
    )
    product_id = fields.Char(
        string="Product ID",
        required=True,
        size=300,
        readonly=True,
        help="Nome da aplicação que gera o SAFT (AO).",
    )
    Product_version = fields.Char(
        string="Product Version",
        size=30,
        required=True,
        readonly=True,
        help="Deve ser indicada a versão da aplicação produtora do ficheiro.",
    )
    header_comment = fields.Char(
        string="Header Comment", size=255, help="Comentários Adicionais"
    )
    warnings = fields.Char("Warnings")

    @api.depends("file_type", "fiscal_year", "start_date", "end_date")
    def _compute_name(self):
        self.name = "XML SAF-T AO %s %s PERIOD %s - %s" % (
            self.file_type or "/",
            self.fiscal_year or "/",
            str(self.start_date)[5:7] or "/",
            str(self.end_date)[5:7] or "/",
        )

    def button_validate(self):
        """f = open('l10n_ao_saft/tests/agt_xml_xsd/validate.xml', 'w')
        f.write(self.text)
        process = subprocess.Popen(
                ['xmllint', '--schema', 'l10n_ao_saft/tests/agt_xml_xsd/I.xsd', f.name, '--noout'],stdout=PIPE, stderr=PIPE)
        out,err = process.communicate()
        f.close()
        os.remove(f.name)
        err = str(err,'utf-8')
        if not 'fails to validate' in err:
            self.state = 'approved'
        else:
            raise ValidationError(err)"""
        self.state = "approved"

    def download(self):
        print("\nID::", self.id)

        return {
            "type": "ir.actions.act_url",
            "url": "/web/download/saft_ao_file/%s" % self.id,
            "target": "new",
        }

    def button_download(self):
        return {
            "type": "ir.actions.act_url",
            "url": "/report/xml/l10n_ao_saft.saft_report/%s" % self.id,
            "target": "new",
        }

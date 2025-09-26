from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains("invoice_date")
    def _check_invoice_date(self):
        for record in self:
            # A restrição deve afetar apenas faturas de clientes (out_invoice)
            if record.move_type == "out_invoice":
                # Verifica se 'invoice_date' está preenchido e se é uma data futura
                if record.invoice_date and record.invoice_date > fields.Date.today():
                    raise ValidationError(
                        "A data da fatura não pode ser superior à data atual."
                    )

                # Busca faturas de clientes com data posterior à nova data da fatura e que não estejam em rascunho
                conflicting_invoices = self.search(
                    [
                        ("move_type", "=", "out_invoice"),  # Apenas faturas de clientes
                        ("invoice_date", ">", record.invoice_date),  # Data posterior
                        ("state", "!=", "draft"),
                    ]
                )

                if conflicting_invoices:
                    raise ValidationError(
                        "A data da fatura não pode ser inferior à de uma fatura já existente no sistema."
                    )

    #  Fatura em estado publicado não pode ser transformado em rascunho
    def button_draft(self):
        pass
        # for record in self:
        #     if record.state == "posted":
        #         raise ValidationError(
        #             "Não é permitido colocar uma fatura já publicada em rascunho."
        #         )

    # Alerta se o valor for inferior ao mínimo para retenção
    @api.onchange("price_subtotal")
    def _check_withholding_threshold_warning(self):
        for record in self:
            withholding_tax = record.invoice_line_ids.mapped("tax_ids").filtered(
                lambda t: t.tax_type_with
            )
            if withholding_tax and record.price_subtotal < min(
                withholding_tax.mapped("threshold_wht"), 20000
            ):
                warning_mess = {
                    "title": ("Atenção!"),
                    "message": (
                        "O valor da fatura aplicado à retenção não pode ser inferior a 20.000 Kz."
                    ),
                }
                return {"warning": warning_mess}

    @api.constrains("invoice_line_ids", "state")
    def _check_invoice_line_validations(self):
        for invoice in self.filtered(
            lambda inv: inv.state != "draft" and inv.move_type == "out_invoice"
        ):
            for line in invoice.invoice_line_ids:

                # Verifica se a linha possui um produto
                if not line.product_id:
                    continue  # Se não houver produto, ignora esta linha

                # Verifica se cada linha de fatura possui um preço unitário maior que zero
                if line.price_unit <= 0:
                    raise ValidationError(
                        (
                            "Incompleto! Todas as linhas da fatura devem ter um preço unitário maior que zero."
                        )
                    )

                # Verifica se cada linha de fatura possui uma unidade de medida
                if not line.product_uom_id:
                    raise ValidationError(
                        (
                            "Incompleto! Todas as linhas da fatura devem ter uma unidade de medida."
                        )
                    )

                # Verifica se cada linha de fatura possui pelo menos um imposto associado
                if not line.tax_ids:
                    raise ValidationError(
                        (
                            "Cada produto deve ter pelo menos um imposto associado. "
                            "Em caso do Produto estar isento de qualquer imposto, adicione o imposto (M21 OU IVA 0%)."
                        )
                    )

                # Verifica se cada linha de fatura possui uma quantidade maior que zero
                if line.quantity <= 0:
                    raise ValidationError(
                        (
                            "Incompleto! Todas as linhas da fatura devem ter uma quantidade."
                        )
                    )

    @api.constrains("invoice_date_due")
    def _check_invoice_date_maturity(self):
        for record in self:
            if (
                record.invoice_date_due
                and record.move_type == "out_invoice"
                and record.invoice_date
                and record.invoice_date_due < record.invoice_date
            ):
                raise ValidationError(
                    "A data de Vencimento nao pode ser menor que a data da factura."
                )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # Não permitir mais de um imposto nas linhas das faturas de clientes
    @api.onchange("tax_ids")
    def _onchange_invoice_line_tax_ids(self):
        for invoice_line in self:
            if (
                invoice_line.move_id.move_type == "out_invoice"
                and len(invoice_line.tax_ids) >= 2
            ):
                warning_mess = {
                    "title": "Atenção!",
                    "message": "Está a utilizar mais do que um imposto!",
                }
                return {"warning": warning_mess}

    # Verificar limiar de retenção para o imposto "RF II 6,5" em faturas de clientes
    @api.onchange("tax_ids", "price_subtotal")
    def _onchange_tax_withholding_threshold(self):
        for line in self:
            if line.move_id.move_type == "out_invoice":
                # Verifica se existe um imposto com o nome "RF II 6,5" e se o subtotal é menor que 20.000
                if (
                    any(tax.name == "RF II 6,5" for tax in line.tax_ids)
                    and line.price_subtotal < 20000
                ):
                    warning_mess = {
                        "title": "Atenção!",
                        "message": (
                            "Para retenção o valor mínimo aplicado deve ser superior ou igual a 20.000 Kz.\n"
                            "Código do Imposto Industrial (Decreto Legislativo Presidencial n.º 2/14, de 20 de outubro de 2014)**:"
                        ),
                    }
                    return {"warning": warning_mess}

    # Verificar se a quantidade é positiva para faturas de clientes
    @api.constrains("quantity")
    def _check_valuePositivoQ(self):
        for invoice_line in self:
            if (
                invoice_line.move_id.move_type == "out_invoice"
                and invoice_line.quantity < 0
            ):
                raise UserError("A quantidade do produto não pode ser negativa.")
        return True

    # Permitir a exclusão apenas se a fatura estiver em rascunho, ou cancelada e sem número ou hash
    def unlink(self):
        for line in self:
            if line.move_id.move_type == "out_invoice" and (
                line.move_id.state != "draft"
                or (
                    line.move_id.state == "cancel"
                    and not line.move_id.internal_number
                    and not line.move_id.hash
                )
            ):
                raise ValidationError(
                    "Aviso\n Apenas é possível eliminar documentos no estado de rascunho."
                )
        return super(AccountMoveLine, self).unlink()

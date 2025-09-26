from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    self_billing_c = fields.Boolean("Self Billing Customer", required=False)
    self_billing_s = fields.Boolean("Self Billing Supplier", required=False)
    vat = fields.Char(string="NIF", default="999999999")

    @staticmethod
    def check_vat(partner):
        if partner.vat and partner.vat != "999999999":
            return partner.vat
        return "Consumidor Final"

    def write(self, values):
        for partner in self:
            if values.get('name') or values.get('vat'):
                invoice_exists = self.env['account.move'].search_count([('state', 'in', ['draft', 'posted', "cancel"]),
                                                                           ("partner_id", "=", partner.id)])
                if invoice_exists:
                    if 'name' in values and values['name'].upper() != partner.name.upper():
                        values.pop('name')
                    """ if 'vat' in values and partner.vat != '999999999':
                        values.pop('vat') """
                    # If  partner has documents don't let uncheck the customer field
                    if 'customer' in values and partner.customer:
                        values.pop("customer")
                    # If  partner has documents don't let uncheck the supplier field
                    if 'supplier' in values and partner.supplier:
                        values.pop("supplier")
                    return super(ResPartner, self).write(values)
            return super(ResPartner, self).write(values)


    def get_content_saf_t_ao(self, start_date=None, end_date=None, company=None):
        result = {
            "Customer": [],
            "Supplier": [],
        }

        processed_partners = set()

        # CORRIGIDO: usa account.move para pesquisar faturas de clientes
        move_model_customer = self.env['account.move'].search([
            ("invoice_date", ">=", start_date),
            ("invoice_date", "<=", end_date),
            ("company_id", "=", company.id),
            ('state', '=', 'posted'),
            #("system_entry_date", "!=", None),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ], order="create_date asc")

        # CORRIGIDO: usa account.move para pesquisar faturas de fornecedores
        move_model_supplier = self.env['account.move'].search([
            ("invoice_date", ">=", start_date),
            ("invoice_date", "<=", end_date),
            ("company_id", "=", company.id),
            ('state', '=', 'posted'),
            #("system_entry_date", "!=", None),
            ('move_type', 'in', ['in_invoice', 'in_refund'])
        ], order="create_date asc")

        partner_model = self.env['res.partner']

        # Garante que o consumidor final seja incluído
        final_consumer = partner_model.search([('ref', '=', 'CF')], limit=1)
        if final_consumer and final_consumer.id not in self.ids:
            self |= final_consumer

        #####################################################################
        # Obter parceiros únicos de faturas de cliente
        customer_partners = move_model_customer.mapped("partner_id")
        customer_partners = customer_partners.filtered(lambda p: p)  # Remove nulos

        # Obter parceiros únicos de faturas de fornecedor
        supplier_partners = move_model_supplier.mapped("partner_id")
        supplier_partners = supplier_partners.filtered(lambda p: p)  # Remove nulos

        # Evitar duplicados
        customer_partner_ids = set(customer_partners.ids)
        supplier_partner_ids = set(supplier_partners.ids)

        # Processar clientes
        for partner in self.env['res.partner'].browse(customer_partner_ids):
            billing_address = {
                "AddressDetail": partner.street or "Desconhecido",
                "City": partner.city or "Desconhecido",
                #"PostalCode": partner.zip or "Desconhecido",
                "Country": partner.country_id.code or "AO"
            }
            ship_address = billing_address.copy()  # Ou customiza se tiver dados diferentes

            result['Customer'].append({
                "CustomerID": partner.id,
                "AccountID": partner.property_account_receivable_id.code or "Desconhecido",
                "CustomerTaxID": partner.vat or "Desconhecido",
                "CompanyName": partner.name,
                "BillingAddress": billing_address,
                "ShipToAddress": ship_address,
                "Email": partner.email or "consumidor@email.com",
                "Website": partner.website or "www.consumidorfinal.co.ao",
                "SelfBillingIndicator": "0" if not partner.self_billing_c else "1"
            })

        # Processar fornecedores
        for partner in self.env['res.partner'].browse(supplier_partner_ids):
            billing_address = {
                "AddressDetail": partner.street or "Desconhecido",
                "City": partner.city or "Desconhecido",
                #"PostalCode": partner.zip or "Desconhecido",
                "Country": partner.country_id.code or "AO"
            }
            ship_address = billing_address.copy()

            result['Supplier'].append({
                "SupplierID": partner.id,
                "AccountID": partner.property_account_payable_id.code or "Desconhecido",
                "SupplierTaxID": partner.vat or "Desconhecido",
                "CompanyName": partner.name,
                "BillingAddress": billing_address,
                "ShipToAddress": ship_address,
                "Email": partner.email or "fornecedor@email.com",
                "Website": partner.website or "www.fornecedorfinal.co.ao",
                "SelfBillingIndicator": "0" if not partner.self_billing_s else "1"
            })

        return result


#         for partner in self:
#             # Evitar processar o mesmo parceiro duas vezes
#             if partner.id in processed_partners:
#                 continue
#             processed_partners.add(partner.id)

#             # Preencher campos obrigatórios
#             if not partner.country_id:
#                 partner.country_id = self.env['res.country'].sudo().search([('code', '=', 'AO')], limit=1)
#             if not partner.city:
#                 partner.city = "Luanda"

#             invoice_address = partner.child_ids.filtered(lambda r: r.type == "invoice")
#             record = invoice_address[0] if invoice_address else partner

#             billing_address = {
#                 "BuildingNumber": "N/A",
#                 "StreetName": record.street or "Desconhecido",
#                 "AddressDetail": record.contact_address or "Desconhecido",
#                 "City": record.city or "Luanda",
#                 "PostalCode": record.zip or "Desconhecido",
#                 "Province": record.state_id.name or "Desconhecido",
#                 "Country": record.country_id.code or "AO"
#             }
#             ship_address = billing_address.copy()
            
#             # Verifica se o parceiro teve faturas
#             customer_partner_ids = move_model.search([
#     ('move_type', 'in', ['out_invoice', 'out_refund']),
#     ('state', '=', 'posted')
# ]).mapped('commercial_partner_id')

# # Obter todos os parceiros com faturas de fornecedor
#             supplier_partner_ids = move_model.search([
#     ('move_type', 'in', ['in_invoice', 'in_refund']),
#     ('state', '=', 'posted')
# ]).mapped('commercial_partner_id')

#             # Cliente
#             if customer_partner_ids:
#                 result['Customer'].append({
#                     "CustomerID": partner.id,
#                     "AccountID": partner.property_account_receivable_id.code or "Desconhecido",
#                     "CustomerTaxID": partner.vat or "Desconhecido",
#                     "CompanyName": partner.name,
#                     "BillingAddress": billing_address,
#                     "ShipToAddress": ship_address,
#                     "Email": partner.email or "consumidor@email.com",
#                     "Website": partner.website or "www.consumidorfinal.co.ao",
#                     "SelfBillingIndicator": "0" if not partner.self_billing_c else "1"
#                 })

#             # Fornecedor
#             if supplier_partner_ids:
#                 result['Supplier'].append({
#                     "SupplierID": partner.id,
#                     "AccountID": partner.property_account_payable_id.code or "Desconhecido",
#                     "SupplierTaxID": partner.vat or "Desconhecido",
#                     "CompanyName": partner.name,
#                     "BillingAddress": billing_address,
#                     "ShipToAddress": ship_address,
#                     "Email": partner.email or "fornecedor@email.com",
#                     "Website": partner.website or "www.fornecedorfinal.co.ao",
#                     "SelfBillingIndicator": "0" if not partner.self_billing_s else "1"
#                 })
#
#        return result

#     def get_content_saf_t_ao(self):
#         result = {
#             "Customer": [],
#             "Supplier": [],
#         }

#         processed_partners = set()
#         partner_model = self.env['res.partner']
#         move_model = self.env['account.move']

#         # Garante que o consumidor final seja incluído
#         final_consumer = partner_model.search([('ref', '=', 'CF')], limit=1)
#         if final_consumer and final_consumer.id not in self.ids:
#             self |= final_consumer

#         for partner in self:
#             # Evitar processar o mesmo parceiro duas vezes
#             if partner.id in processed_partners:
#                 continue
#             processed_partners.add(partner.id)

#             # Preencher campos obrigatórios
#             if not partner.country_id:
#                 partner.country_id = self.env['res.country'].sudo().search([('code', '=', 'AO')], limit=1)
#             if not partner.city:
#                 partner.city = "Luanda"

#             invoice_address = partner.child_ids.filtered(lambda r: r.type == "invoice")
#             record = invoice_address[0] if invoice_address else partner

#             billing_address = {
#                 "BuildingNumber": "N/A",
#                 "StreetName": record.street or "Desconhecido",
#                 "AddressDetail": record.contact_address or "Desconhecido",
#                 "City": record.city or "Luanda",
#                 "PostalCode": record.zip or "Desconhecido",
#                 "Province": record.state_id.name or "Desconhecido",
#                 "Country": record.country_id.code or "AO"
#             }
#             ship_address = billing_address.copy()
            
#             # Verifica se o parceiro teve faturas
#             customer_partner_ids = move_model.search([
#     ('move_type', 'in', ['out_invoice', 'out_refund']),
#     ('state', '=', 'posted')
# ]).mapped('commercial_partner_id')

# # Obter todos os parceiros com faturas de fornecedor
#             supplier_partner_ids = move_model.search([
#     ('move_type', 'in', ['in_invoice', 'in_refund']),
#     ('state', '=', 'posted')
# ]).mapped('commercial_partner_id')

#             # Cliente
#             if customer_partner_ids:
#                 result['Customer'].append({
#                     "CustomerID": partner.id,
#                     "AccountID": partner.property_account_receivable_id.code or "Desconhecido",
#                     "CustomerTaxID": partner.vat or "Desconhecido",
#                     "CompanyName": partner.name,
#                     "BillingAddress": billing_address,
#                     "ShipToAddress": ship_address,
#                     "Email": partner.email or "consumidor@email.com",
#                     "Website": partner.website or "www.consumidorfinal.co.ao",
#                     "SelfBillingIndicator": "0" if not partner.self_billing_c else "1"
#                 })

#             # Fornecedor
#             if supplier_partner_ids:
#                 result['Supplier'].append({
#                     "SupplierID": partner.id,
#                     "AccountID": partner.property_account_payable_id.code or "Desconhecido",
#                     "SupplierTaxID": partner.vat or "Desconhecido",
#                     "CompanyName": partner.name,
#                     "BillingAddress": billing_address,
#                     "ShipToAddress": ship_address,
#                     "Email": partner.email or "fornecedor@email.com",
#                     "Website": partner.website or "www.fornecedorfinal.co.ao",
#                     "SelfBillingIndicator": "0" if not partner.self_billing_s else "1"
#                 })

#         return result



    # def get_content_saf_t_ao(self):
    #     result = {
    #         "Customer": [],
    #         "Supplier": [],
    #     }

    #     processed_partners = set()

    #     for partner in self:
    #         if not partner.country_id:
    #             partner.country_id = self.env['res.country'].sudo().search([('code', '=', 'AO')], limit=1)
    #         if not partner.city:
    #             partner.city = "Luanda"

    #         invoice_address = partner.child_ids.filtered(lambda r: r.type == "invoice")
    #         record = invoice_address[0] if invoice_address else partner

    #         billing_address = {
    #             "BuildingNumber": "N/A",
    #             "StreetName": record.street or "Desconhecido",
    #             "AddressDetail": record.contact_address or "Desconhecido",
    #             "City": record.city or "Luanda",
    #             "PostalCode": record.zip or "Desconhecido",
    #             "Province": record.state_id.name or "Desconhecido",
    #             "Country": record.country_id.code or "AO"
    #         }

    #         ship_address = billing_address.copy()

    #         # Evitar duplicados
    #         key = f"{partner.id}-{partner.vat}"
    #         if key in processed_partners:
    #             continue
    #         processed_partners.add(key)
    #         if partner.customer:
    #             result['Customer'].append({
    #                 "CustomerID": partner.id,
    #                 "AccountID": partner.property_account_receivable_id.code or "Desconhecido",
    #                 "CustomerTaxID": partner.vat or "Desconhecido",
    #                 "CompanyName": partner.name,
    #                 "BillingAddress": billing_address,
    #                 "ShipToAddress": ship_address,
    #                 "Email": partner.email or "consumidor@email.com",
    #                 "Website": partner.website or "www.consumidorfinal.co.ao",
    #                 "SelfBillingIndicator": "0" if not partner.self_billing_c else "1"
    #             })

    #         if partner.supplier:
    #             result['Supplier'].append({
    #                 "SupplierID": partner.id,
    #                 "AccountID": partner.property_account_payable_id.code or "Desconhecido",
    #                 "SupplierTaxID": partner.vat or "Desconhecido",
    #                 "CompanyName": partner.name,
    #                 "BillingAddress": billing_address,
    #                 "ShipToAddress": ship_address,
    #                 "Email": partner.email or "fornecedor@email.com",
    #                 "Website": partner.website or "www.fornecedorfinal.co.ao",
    #                 "SelfBillingIndicator": "0" if not partner.self_billing_s else "1"
    #             })

    #     # Verificação especial para o consumidor final (CF)
    #     final_consumer = self.env['res.partner'].search([('ref', '=', 'CF')], limit=1)
    #     if final_consumer and final_consumer.id not in [p.id for p in self]:
    #         self |= final_consumer
    #         # Reprocessar o CF
    #         return self.get_content_saf_t_ao()

    #     return result

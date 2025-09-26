from odoo import fields, models, api
from . import utils


class SAFTStockMove(models.Model):
    _inherit = 'stock.move'

    hash = fields.Char(string="Key", default="0")
    hash_control = fields.Char(
        string="Key Version", relate='company_id.key_version')
    system_entry_date = fields.Datetime("Signature Datetime")
    movement_type = fields.Selection(string="Movement Type", size=2,
                                     selection=[('GR', 'Guia de remessa'),
                                                ('GT', 'Guia de transporte(Incluir aqui as guias globais).'),
                                                ('GA', 'Guia de movimentação de activos fixos próprios'),
                                                ('GC', 'Guia de consignação'),
                                                ('GD', 'Guia ou nota de devolução.')],
                                     help="Tipo de documento")

    def get_content_to_sign(self):
        for res in self:
            _last_stock_move = self.env['stock.move'].search(
                [('number', '<', res.number), ('state', 'in', ['open', 'paid', 'cancel']), ], order="number")
            _last_stock_move = _last_stock_move.filtered(lambda r: r.date_invoice[:4] == res.date_invoice[:4])
            total = utils.gross_total(0.0)
            last_stock_hash = ""
            if _last_stock_move:
                last_stock_hash = _last_stock_move[-1].hash
                content = (
                    res.date_invoice, res.system_entry_date.replace(' ', 'T'), res.sequence_number, str(total),
                    last_stock_hash)
                return ";".join(content)
            else:
                content = (
                    res.date_invoice, res.system_entry_date.replace(' ', 'T'), res.sequence_number, str(total))
                return ";".join(content) + ';'

    def get_content_saf_t_ao(self):

        result = {
            "MovementOfGoods": {

                "NumberOfMovementLines": "",
                "TotalQuantityIssued": "",
                "StockMovement": [],

            }
        }

        stock_movement = self.filtered(lambda r: r.state in ['done', 'assigned', 'cancel'])
        for st_movement in stock_movement:
            status_code = 'N'
            if st_movement.state == 'cancel':
                status_code = 'A'
            sale_order = st_movement.line_id.mapped("order_id")
            stock_movement = {

                "DocumentNumber": utils.ref_no(st_movement.reference),

                "DocumentStatus": {

                    "MovementStatus": status_code,
                    "MovementStatusDate": st_movement.write_date.replace(' ', 'T'),
                    "Reason": "",
                    "SourceID": st_movement.write_uid.id,
                    "SourceBilling": "P"
                },

                "Hash": 0,
                "HashControl": self.env.user.company_id.key_version,
                "Period": int(st_movement.date[5:7]),
                "MovementDate": st_movement.create_date,
                "MovementType": st_movement.movement_type,
                "SystemEntryDate": st_movement.system_entry_date.replace(' ', 'T'),
                # "TransactionID": "%s %s %s" % (
                # st_movement.move_id.date, inv.journal_id.code.replace(' ', ''),
                # inv.move_id.name.replace(' ', '').replace('/', '')),
                "CustomerID": st_movement.partner_id.id if st_movement.picking_code == 'outgoing' else "",
                "SupplierID": st_movement.partner_id.id if st_movement.picking_code == 'incoming' else "",
                "SourceID": st_movement.create_uid.id,
                # "EACCode": "",
                "MovementComments": st_movement.origin,
                "ShipTo": [{

                    "DeliveryID": picking.partner_id.partner_id.contact_address + ' ' + picking.partner_id.vat,
                    "DeliveryDate": picking.date_done,
                    "WarehouseID": picking.location_dest_id.name,
                    "LocationID": picking.location_id.name,
                    "Address": {
                        "BuildingNumber": "",
                        "StreetName": picking.partner_id.street,
                        "AddressDetail": picking.partner_id.contact_address,
                        "City": picking.partner_id.city,
                        "PostalCode": picking.partner_id.zip,
                        "Province": picking.partner_id.state_id.name,
                        "Country": picking.partner_id.country_id.code
                    }

                } for picking in st_movement.picking_id],
                "ShipFrom": [{
                    "DeliveryID": "",
                    "DeliveryDate": "",
                    "WarehouseID": "",
                    "LocationID": picking.location_id.name,
                    "Address": {
                        "BuildingNumber": "",
                        "StreetName": picking.partner_id.street,
                        "AddressDetail": picking.partner_id.contact_address,
                        "City": picking.partner_id.city,
                        "PostalCode": picking.partner_id.zip,
                        "Province": picking.partner_id.state_id.name,
                        "Country": picking.partner_id.country_id.code
                    }

                } for picking in st_movement.picking_id],
                "MovementEndTime": st_movement.picking_id.date_done,
                "MovementStartTime": st_movement.picking_id.date_done,
                "AGTDocCodeID": "",
                "Line": [{
                    "LineNumber": "",
                    "OrderReferences": {
                        "OriginatingON": "",
                        "OrderDate": sale_order.date_order
                    },
                    "ProductCode": st_movement.product_id.id,
                    "ProductDescription": utils.remove_special_chars(st_movement.product_id.description.strip()[:200]),
                    "Quantity": st_movement.product_qty,
                    "UnitOfMeasure": st_movement.product_id.uom_name,
                    "UnitPrice": utils.gross_total(st_movement.product_id.price),
                    "Description": utils.remove_special_chars(st_movement.name.strip()[:200]),
                    "ProductSerialNumber": st_movement.product_id.default_code or "S/N",
                    "DebitAmount": 0.00,
                    "CreditAmount": utils.gross_total(line.price_subtotal) or 0.00,
                    "Tax": [{
                        "TaxType": tax.saft_tax_type,
                        "TaxCountryRegion": tax.country_region,
                        "TaxCode": tax.saft_tax_code,
                        "TaxPercentage": tax.amount if tax.amount_type in ["percent", "division"] else 0.00,
                        "TaxAmount": utils.gross_total(tax.amount) if tax.amount_type in ["fixed"] else 0.00,
                    } for tax in line.tax_id if tax.tax_on == "invoice"],
                    "TaxExemptionReason": line.tax_id.filtered(
                        lambda r: r.amount == 0)[0].exemption_reason if line.tax_id.filtered(
                        lambda r: r.amount == 0) else "",
                    "TaxExemptionCode": line.tax_id.filtered(
                        lambda r: r.amount == 0)[0].saft_tax_code if line.tax_id.filtered(
                        lambda r: r.amount == 0) else "",
                    "SettlementAmount": line.discount,
                    "CustomsInformation": {
                        "ARCNo": "",
                        "IECAmount": ""
                    },
                } for line in st_movement.sale_line_id],
                "DocumentTotals": [{
                    "TaxPayable": sale.amount_tax,
                    "NetTotal": utils.gross_total(sale.amount_untaxed),
                    "GrossTotal": utils.gross_total(sale.amount_total),
                    "Currency": {
                        "CurrencyCode": sale.currency_id.name,
                        "CurrencyAmount": utils.gross_total(sale.amount_total),
                        "ExchangeRate": sale.currency_id.rate
                    }
                } for sale in sale_order]

            }
            result['MovementOfGoods']['StockMovement'].append(stock_movement)
        result['MovementOfGoods']['NumberOfMovementLines'] = len(stock_movement)

        return result

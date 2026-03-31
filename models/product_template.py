# -*- coding: utf-8 -*-
import base64
from odoo import api, fields, models, SUPERUSER_ID
from odoo import models, fields, api, _
from datetime import datetime
from io import StringIO, BytesIO
import logging
import json
import requests


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_variant_id = fields.Many2one(
        'product.product', 
        compute="_compute_product_variant_id", 
        store=True, 
        search=True
    )

    #Number of Packages
    packages_number = fields.Integer(string='Paquetes que componen el SKU', help="Indica en cuántas cajas/paquetes se envía este SKU debido a su tamaño (valor entero).")
    #Product Measurements
    product_length = fields.Float(string='Largo producto', help="Largo del Producto en centimentros")
    product_height = fields.Float(string='Alto producto', help="Alto del Producto en centimentros")
    product_width = fields.Float(string='Ancho producto', help="Ancho del Producto en centimentros")
    product_weight = fields.Float(string='Peso producto', help="Peso del Producto en kilogramos")
    product_volume = fields.Float(string='Volumen producto', help="Volumen del Producto", compute='_volumen')
    #Packaging Measurements
    packing_length = fields.Float(string='Largo empaque', help="Largo del Empaque en centimentros")
    packing_height = fields.Float(string='Alto empaque', help="Alto del Empaque en centimentros")
    packing_width = fields.Float(string='Ancho empaque', help="Ancho del Empaque en centimentros")
    packing_weight = fields.Float(string='Peso empaque', help="Peso del Empaque en centimentros")
    #Comercial
    #buyer = fields.One2many('usr.comprador', inverse_name='partner_id', string='Comprador responsable', help="Comprador responsable del SKU")
    buyer = fields.Many2one('product.responsible', string='Comprador responsable', help='Establece el comprador encargado de este SKU', domain="[('type', 'in', ['buyer', 'both'])]")
    owner = fields.Many2one('product.responsible', string='Owner comercial', help='Establece el comercial responsable de este SKU', domain="[('type', 'in', ['owner', 'both'])]")
    internal_category = fields.Many2one('internal.category', string='Categoría interna', help='Categoría interna para el equipo de SR')
    brand = fields.Many2one('product.brand', string='Marca', help='Marca a la que pertecene el SKU')
    #Logistics
    nacional_import = fields.Selection([('importado', 'Importado'),
                                        ('nacional', 'Nacional')],
                                       string='Importacion/Nacional', help="Indica si el producto es importado o nacional")
    status = fields.Many2one('product.estatus', string='Estatus', help='Estatus del producto')
    substatus = fields.Many2one('product.subestatus', string='Subestatus', help='Subestatus del producto')#, domain=[('status_subsequence', "=", 'status_sequence')])
    status_sequence = fields.Char(related='status.sequence', string='Secuencia')
    status_subsequence = fields.Char(related='substatus.subsequence', string='Subsecuencia')

    #Planning
    clasificacion_abc = fields.Char(string='Clasificación abc', help='Clasificación desarrollada por Planning')

    
    #Costs
    previous_cost = fields.Float(related='product_variant_id.previous_cost', string='Costo anterior', help='Muestra el costo anterior del producto')
    
    #Substitute, Mirror and Variants
    substitute = fields.One2many('prod.relacionado', inverse_name='product_id', string='Productos', help='Muestra un producto que podría sustituir o reemplazar al seleccionado')

    #Location
    location_hallway = fields.Char(string="Pasillo")
    location_level = fields.Char(string="Nivel")
    location_area = fields.Char(string="Zona")
    location_box = fields.Char(string="Caja")
    #Label
    txt_filename = fields.Char()
    txt_binary = fields.Binary("Etiqueta ZPL")
    
    # Campos Cecilia  22-oct-2024
    data_averages_updated_date = fields.Datetime(string='Medidas actualizadas el', help='Establece la fecha en que se actualizaron las medidas')
    data_averages_updated_by = fields.Many2one('res.users', string='Medidas actualizadas por', help='Establece el usuario que actualizó las medidas')


    #Campo de wb_product_import V15.0
    #IMPORTACION
    tariff_percentage = fields.Float(string='Porcentaje de arancel', help="Porcentaje Impuesto del Arancel")
    
    # Function that prints the previous cost
    @api.depends('seller_ids')
    def _previous_cost(self):
        #self.ensure_one()
        _logger = logging.getLogger(__name__)
        for each in self:
            if each.default_code or each.default_code != '':
                product_search = each.env['product.product'].search([('default_code', '=', each.default_code)], limit=1)
                all_seller_ids = product_search.seller_ids.ids
                _logger.info('seller_ids: %s', all_seller_ids)

                if len(all_seller_ids) < 1:
                    each.previous_cost = 0.0
                else:
                    if all_seller_ids:
                        id_ultimo_costo = all_seller_ids[-1]
                        supplier = each.env['product.supplierinfo'].search([('id', '=', id_ultimo_costo)])
                        each.previous_cost = supplier.price
                        _logger.info('Costo anterior: %s', each.previous_cost)

                        if len(all_seller_ids) > 1:
                            if each.previous_cost == 0.0:
                                id_ultimo_costo = all_seller_ids[-2]
                                supplier = each.env['product.supplierinfo'].search([('id', '=', id_ultimo_costo)])
                                each.previous_cost = supplier.price
                                _logger.info('Costo anterior: %s', each.previous_cost)
                                if len(all_seller_ids) > 2:
                                    if each.previous_cost == 0.0:
                                        id_ultimo_costo = all_seller_ids[-3]
                                        supplier = each.env['product.supplierinfo'].search([('id', '=', id_ultimo_costo)])
                                        each.previous_cost = supplier.price
                                        _logger.info('Costo anterior: %s', each.previous_cost)
                                    else:
                                        _logger.info('Registro [-3] no es igual a 0.0')
                            else:
                                _logger.info('Registro [-2] no es igual a 0.0')
                    else:
                        each.previous_cost = 0.0
            else:
                _logger.info('No se encontró el SKU')

    # Function that prints the last cost
    @api.depends('seller_ids')
    def _last_cost(self):
        self.ensure_one()

        _logger = logging.getLogger(__name__)
        if self.default_code or self.default_code != '':
            product_search = self.env['product.product'].search([('default_code', '=', self.default_code)], limit=1)
            all_seller_ids = product_search.seller_ids.ids
            _logger.info('seller_ids: %s', all_seller_ids)

            if len(all_seller_ids) <= 1:
                self.last_entry_cost = 0.0
            else:
                if all_seller_ids:
                    id_ultimo_costo = all_seller_ids[-1]
                    supplier = self.env['product.supplierinfo'].search([('id', '=', id_ultimo_costo)])
                    self.last_entry_cost = supplier.price
                    _logger.info('Costo anterior: %s', self.last_entry_cost)

                    if self.last_entry_cost == 0.0:
                        id_ultimo_costo = all_seller_ids[-2]
                        supplier = self.env['product.supplierinfo'].search([('id', '=', id_ultimo_costo)])
                        self.last_entry_cost = supplier.price
                        _logger.info('Costo anterior: %s', self.last_entry_cost)

                        if self.last_entry_cost == 0.0:
                            id_ultimo_costo = all_seller_ids[-3]
                            supplier = self.env['product.supplierinfo'].search([('id', '=', id_ultimo_costo)])
                            self.last_entry_cost = supplier.price
                            _logger.info('Costo anterior: %s', self.last_entry_cost)
                        else:
                            _logger.info('Registro [-3] no es igual a 0.0')
                    else:
                        _logger.info('Registro [-3] no es igual a 0.0')
                else:
                    self.last_entry_cost = 0.0

    #Function that prints the replacement cost
    @api.depends('seller_ids')
    def _replacement_cost(self):
        self.ensure_one()

        _logger = logging.getLogger(__name__)
        if self.default_code or self.default_code != '':
            product_search = self.env['product.product'].search([('default_code', '=', self.default_code)], limit=1)
            all_seller_ids = product_search.seller_ids.ids
            _logger.info('seller_ids: %s', all_seller_ids)

            if len(all_seller_ids) <= 1:
                self.replacement_cost = 0.0
            else:
                if all_seller_ids:
                    id_ultimo_costo = all_seller_ids[-1]
                    supplier = self.env['product.supplierinfo'].search([('id', '=', id_ultimo_costo)])
                    self.replacement_cost = supplier.price
                    _logger.info('Costo ultimo: %s', self.replacement_cost)

                    if self.replacement_cost == 0.0:
                        id_ultimo_costo = all_seller_ids[-2]
                        supplier = self.env['product.supplierinfo'].search([('id', '=', id_ultimo_costo)])
                        self.replacement_cost = supplier.price
                        _logger.info('Costo ultimo: %s', self.replacement_cost)

                        if self.replacement_cost == 0.0:
                            id_ultimo_costo = all_seller_ids[-3]
                            supplier = self.env['product.supplierinfo'].search([('id', '=', id_ultimo_costo)])
                            self.replacement_cost = supplier.price
                            _logger.info('Costo ultimo: %s', self.replacement_cost)
                        else:
                            _logger.info('Registro [-3] no es igual a 0.0')
                    else:
                        _logger.info('Registro [-2] no es igual a 0.0')
                else:
                    self.replacement_cost = 0.0

    #Function that prints the ZPL label of the SKU
    def print_zpl(self):
        _logger = logging.getLogger(__name__)

        ahora = datetime.now()
        fecha = ahora.strftime("%Y-%m-%d %H:%M:%S")

        dato = self
        content = ''

        for record in self:
            content += '^XA' + '\n'
            content += '^CFA,40' + '\n'
            content += '^FO15,60^FD' + str(record.default_code) + '^FS' + '\n'
            content += '^CFA,30' + '\n'
            content += '^FO15,100^FD' + str(record.name) + '^FS' + '\n'
            content += '^FO15,140^FD' + "PASILLO:" + str(record.location_hallway) + "NIVEL:" + str(
                record.location_level) + "PARED:" + str(record.location_area) + "CAJA:" + str(
                record.location_box) + '^FS' + '\n'
            content += '^FO15,180^FD' + str(fecha) + '^FS' + '\n'
            content += '^BY4,3,100' + '\n'
            content += '^FO45,240^BC^FD' + str(record.barcode) + '^FS' + '\n'
            content += '^Xz'

            headers = {'Content-Type': 'application/json'}
            # content_base64 = base64.encodestring(content.encode('utf-8'))
            b = content.encode("UTF-8")
            content_base64 = base64.b64encode(b)

            _logger.info('content_base64: %s ', content_base64)
            data = '{\n"printerId": "69183018",\n "title": "Prueba de Impresion",\n "contentType": "raw_base64",\n  "content":' + str(
                content_base64)[1:].replace("'", '"') + ',\n  "source": "Odoo Product Label ZPL"\n }'
            _logger.info('data: %s ', data)
            response = requests.post('https://api.printnode.com/printjobs', headers=headers, data=data,
                                     auth=('JClDsEj9_8tbYVQ_9C6kZ8CSi8HydNWYcvcg_KuQZQo', ''))
            _logger.info('Respuesta PrintNode: %s ', response.text)

            # raise Warning("Etiqueta ZPL creada")
        return self.write({
            'txt_filename': str(record.default_code) + '.zpl',
            'txt_binary': base64.encodestring(content.encode('utf-8'))
        })

    #Function that print the actual stock
    @api.depends('stock_exclusivas', 'stock_urrea')
    def _total(self):
        _logger = logging.getLogger(__name__)
        for each in self:
            try:
                quantity_total = 0
                reserved_quantity_total = 0

                # Use the main variant of the template
                product = each.product_variant_id
                if not product:
                    each.stock_real = 0
                    continue

                quants = product.stock_quant_ids
                for quant in quants:
                    location = quant.location_id
                    location_display_name = location.display_name
                    quantity = quant.quantity
                    reserved_quantity = quant.reserved_quantity
                    previsto = quantity - reserved_quantity

                    # --- Todo lo que esta en las ubicaciones AG
                    if location_display_name and 'AG/Stock' in location_display_name:
                        quantity_total += quantity
                        reserved_quantity_total += reserved_quantity

                each.stock_real = quantity_total - reserved_quantity_total

                # --- Calculando el stock para los marketplaces
                if each.stock_markets == 0:
                    each.stock_mercadolibre = each.stock_real + each.stock_exclusivas + each.stock_urrea
                else:
                    each.stock_mercadolibre = each.stock_markets

                if each.stock_mercadolibre < 0:
                    each.stock_mercadolibre = 0

                if each.stock_markets == 0:
                    each.stock_linio = each.stock_real + each.stock_exclusivas
                else:
                    each.stock_linio = each.stock_markets

                if each.stock_linio < 0:
                    each.stock_linio = 0

                if each.stock_markets == 0:
                    each.stock_amazon = each.stock_real + each.stock_exclusivas + each.stock_urrea
                else:
                    each.stock_amazon = each.stock_markets

                if each.stock_amazon < 0:
                    each.stock_amazon = 0

            except Exception as e:
                _logger.error('ODOO CALCULATE|' + str(e))

    #Function that print the actual stock
    @api.depends('stock_real')
    def _min_stock_markets(self):
        _logger = logging.getLogger(__name__)
        for each in self:
            try:
                # --- Adecuacion para cuando el producto es un combo "is_kit=True"
                lista_stock_markets = []
                lista_stock_real = []

                product = each.product_variant_id
                if not product or not product.bom_ids:
                    continue
                
                # Check if it's a kit using the first BOM
                bom = product.bom_ids[0]
                if bom.type != 'phantom':
                    continue

                sub_product_line_ids = bom.bom_line_ids
                for line in sub_product_line_ids:
                    product_id = line.product_id
                    product_quantity = line.product_qty or 1.0

                    stock_markets_subproductos = product_id.stock_markets

                    # -- para los combos cuando vienen varios productos
                    stock_real_subproducto = int(int(product_id.stock_real) / product_quantity)

                    stock_exclusivas_subproducto = product_id.stock_exclusivas
                    stock_urrea_subproducto = product_id.stock_urrea

                    if stock_markets_subproductos <= 0:
                        stock_subproducto_markets = stock_real_subproducto + stock_exclusivas_subproducto + stock_urrea_subproducto
                    else:
                        stock_subproducto_markets = stock_markets_subproductos

                    lista_stock_markets.append(stock_subproducto_markets)
                    lista_stock_real.append(stock_real_subproducto)
                
                if lista_stock_markets:
                    stock_minimo_markets = min(lista_stock_markets)
                    stock_minimo_real = min(lista_stock_real)
                    each.stock_markets = stock_minimo_markets
                    each.stock_real = stock_minimo_real

            except Exception as e:
                _logger.info('ERROR _min_stock_markets(): | %s', str(e))

    #Function that print VAT price
    @api.depends('list_price')
    def _price_vat(self):
        self.ensure_one()
        if self.list_price:
            self.vat_price = round(float(self.list_price)*1.16, 0)
        else:
            self.vat_price=0.00

    #Function that print the volume of product
    @api.depends('product_width','product_height','product_length')
    def _volumen(self):
        _logger = logging.getLogger(__name__)
        for rec in self:
            if rec.product_width > 0 and rec.product_height > 0 and rec.product_length > 0:
                rec.product_volume = round( (rec.product_width * rec.product_height * rec.product_length) / 5000,2)
            else:
                rec.product_volume = 0.00
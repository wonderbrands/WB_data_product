from odoo import models, fields, api

class ProductProductExtraFields(models.Model):
    _inherit = 'product.product'

    security_stock = fields.Integer(string="Stock de seguridad")
    visualization_stock = fields.Integer(string="Stock de visualización de canal")
    pvp_aim = fields.Float(string="PVP objetivo")
    purchase_frequency = fields.Integer(string="Frecuencia de compra")
    pc1 = fields.Float(string="PC1")
    pc2 = fields.Float(string="PC2")
    cluster = fields.Char(string="Cluster")
    loading_qty_ = fields.Float(string="Cantidad de carga")
    data_inventory_date = fields.Date(string="Fecha de inventario")
    data_supplier_code = fields.Char(string="Código de proveedor")

    target_items = fields.Integer(string="Venta objetivo")
    purchase_active = fields.Boolean(string="Compra activa")
    variant = fields.Char(string="Variante")
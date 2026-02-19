from odoo import models, fields

class ProductResponsible(models.Model):
    _name = 'product.responsible'
    _description = 'Responsables de Producto'

    name = fields.Char(string='Nombre', required=True)
    email = fields.Char(string='Correo Electrónico')
    phone = fields.Char(string='Teléfono')
    company = fields.Char(string='Empresa/Departamento')
    address = fields.Text(string='Dirección')
    active = fields.Boolean(default=True)
    
    type = fields.Selection([
        ('buyer', 'Comprador'),
        ('owner', 'Owner Comercial'),
        ('both', 'Ambos')
    ], string='Tipo', default='both')

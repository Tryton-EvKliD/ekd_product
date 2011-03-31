#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Not, Bool, Eval
from trytond.transaction import Transaction

STATES = {
    'readonly': Not(Bool(Eval('active'))),
}

_TYPE_PRODUCT=[
        ('stockable', 'Stockable'),
        ('container', 'Container'),
        ('exploited', 'Exploited'),
        ('consumable', 'Consumable'),
        ('service', 'Service')
        ]

class ProductTemplate(ModelSQL, ModelView):
    "Product Template"
    _name = "ekd.product.template"
    _description = __doc__

    name = fields.Char('Name', size=None, required=True)
    type = fields.Selection(_TYPE_PRODUCT, 'Type', required=True, states=STATES)
    category = fields.Many2One('product.category','Category')
    group = fields.Many2One('product.group','Group')
    default_uom = fields.Many2One('product.uom', 'Default UOM')
    active = fields.Boolean('Active')
    description = fields.Text('Description')
    properties = fields.One2Many('ekd.product.template.property', 'product', 'Property')

    def default_active(self):
        return True

    def default_type(self):
        return 'stockable'

ProductTemplate()

class PropertyTypeValue(ModelSQL, ModelView):
    "Property Type Value"
    _name = "ekd.product.template.property.type_value"
    _description = __doc__

    key = fields.Char('Key Property', size=80)
    name = fields.Char('Property', size=128, required=True, translate=True)

PropertyTypeValue()

class ProductTemplateProperty(ModelSQL, ModelView):
    "Product Template Property"
    _name = "ekd.product.template.property"
    _description = __doc__

    product = fields.Many2One('ekd.product.template', 'Product Template',
            required=True, ondelete='CASCADE', select=1)
    name = fields.Char('Property', size=None, required=True,
            select=1)
    range = fields.Char('Range of Values', size=None)
    value_default = fields.Char('Default Value', size=None)
    default_uom = fields.Many2One('product.uom', 'UOM')
    type_value = fields.Many2One('ekd.product.template.property.type_value', 'Type Value')

ProductTemplateProperty()

class Template(ModelSQL, ModelView):
    "Product Template"
    _name = "product.template"
    _description = __doc__

    name = fields.Char('Name', size=None, required=True, translate=True,
            select=1, states=STATES)
    type = fields.Selection(_TYPE_PRODUCT, 'Type', required=True, states=STATES)
    category = fields.Many2One('product.category','Category', required=True,
            states=STATES)
    group = fields.Many2Many('product.grouping', 'product', 'group', 'Group', states=STATES)
    default_uom = fields.Many2One('product.uom', 'Default UOM', required=True,
            states=STATES)
    active = fields.Boolean('Active', select=1)
    products = fields.One2Many('product.product', 'template', 'Products',
            states=STATES)
    analogue = fields.Many2Many('ekd.product.analogue', 'original', 'product','Product Analogue', select=1)
    product_template = fields.Many2One('ekd.product.template', 'Product Template',
                            on_change=['product_template', 'properties', 'description'])
    properties = fields.One2Many('ekd.product.property', 'product', 'Property', select=2)
    as_material = fields.Boolean('As Material', select=1)
    as_fixed = fields.Boolean('As Fixed Assets', select=1)
    as_intangible = fields.Boolean('As Intangible Assets', select=1)
    as_goods = fields.Boolean('As Goods', select=1)

    def default_active(self):
        return True

    def default_type(self):
        return 'stockable'

    def default_cost_price_method(self):
        return 'fixed'

    def get_price_uom(self, ids, name):
        product_uom_obj = self.pool.get('product.uom')
        res = {}
        field = name[:-4]
        context = Transaction().context
        if context.get('uom'):
            to_uom = self.pool.get('product.uom').browse(
                Transaction().context['uom'])
            for product in self.browse(ids):
                res[product.id] = product_uom_obj.compute_price(
                        product.default_uom, product[field],
                        to_uom)
        else:
            for product in self.browse(ids):
                res[product.id] = product[field]
        return res

    def copy(self, ids, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['products'] = False
        return super(Template, self).copy(ids, default=default)

Template()

class ProductGrouping(ModelSQL, ModelView):
    "Product Grouping"
    _name = 'product.grouping'

    product = fields.Many2One('product.template', 'Product Template',
            required=True, ondelete='CASCADE', select=1)
    group = fields.Many2One('product.group', 'Product Group',
            required=True, ondelete='CASCADE', select=1)
    
ProductGrouping()

class Product(ModelSQL, ModelView):
    "Product"
    _name = "product.product"
    _description = __doc__
    _inherits = {'product.template': 'template'}

    template = fields.Many2One('product.template', 'Product Template',
            required=True, ondelete='CASCADE', select=1)
    code = fields.Char("Code", size=None, select=1)
    description = fields.Text("Description")
    id_1c = fields.Char("ID import from 1C", size=None, select=1)

    def get_rec_name(self, ids, name):
        if not ids:
            return {}
        res = {}
        for product in self.browse(ids):
            name = product.name
            if product.code:
                name = '[' + product.code + '] ' + product.name
            res[product.id] = name
        return res

    def search_rec_name(self, name, clause):
        ids = self.search([('code',) + clause[1:]],
                order=[])
        if ids:
            ids += self.search([('name',) + clause[1:]],
                    order=[])
            return [('id', 'in', ids)]
        return [('name',) + clause[1:]]

    def delete(self, ids):
        template_obj = self.pool.get('product.template')

        if isinstance(ids, (int, long)):
            ids = [ids]

        # Get the templates before we delete the products.
        products = self.browse(ids)
        template_ids = [product.template.id for product in products]

        res = super(Product, self).delete(ids)

        # Get templates that are still linked after delete.
        templates = template_obj.browse(template_ids)
        unlinked_template_ids = [template.id for template in templates \
                                 if not template.products]
        if unlinked_template_ids:
            template_obj.delete(unlinked_template_ids)

        return res

    def copy(self, ids, default=None):
        template_obj = self.pool.get('product.template')

        int_id = False
        if isinstance(ids, (int, long)):
            int_id = True
            ids = [ids]
        if default is None:
            default = {}

        default = default.copy()
        default['products'] = False
        new_ids = []
        for product in self.browse(ids):
            default['template'] = template_obj.copy(product.template.id)
            new_id = super(Product, self).copy(product.id, default=default)
            new_ids.append(new_id)
        if int_id:
            return new_ids[0]
        return new_ids

    def on_change_product_template(self, vals):
        if not vals.get('product_template', False):
            return {}
        product_tmpl_obj = self.pool.get('ekd.product.template')
        product_tmpl_id = product_tmpl_obj.browse(vals.get('product_template'))
        properties_new = {}
        if not vals.get('properties', False):
            for line_prop in product_tmpl_id.properties:
                properties_new.setdefault('add', []).append({
                    'key_name': line_prop.id,
                    'key':line_prop.name,
                    'value': '',
                    })
        else:
            #for line_prop in vals.get('properties', []): 
                #if line_prop.get('key_name'):
            #    else:
            for line_prop in product_tmpl_id.properties:
                properties_new.setdefault('add', []).append({
                    'key_name': line_prop.id,
                    'key':line_prop.name,
                    'value': '',
                    })

        return {
                'name': product_tmpl_id.name,
                'description': product_tmpl_id.description,
                'properties': properties_new,
                'category': product_tmpl_id.category.id,
                'default_uom': product_tmpl_id.default_uom.id,
                'group': product_tmpl_id.group.id,
                'type': product_tmpl_id.type,
                }

Product()

class ProductProperty(ModelSQL, ModelView):
    "Product Property"
    _name = "ekd.product.property"
    _description = __doc__

    product = fields.Many2One('product.product', 'Product Template',
            required=True, ondelete='CASCADE', select=1)
    key_name = fields.Many2One('ekd.product.template.property', 'Property')
    key = fields.Char('Property', size=None, required=True, translate=True,
            select=1)
    value = fields.Char('Value', size=None, required=True,
            select=1)
    default_uom = fields.Many2One('product.uom', 'UOM')
    type_value = fields.Many2One('ekd.product.template.property.type_value', 'Type Value')

ProductProperty()

class ProductAnalogue(ModelSQL, ModelView):
    "Product Analogue"
    _name = "ekd.product.analogue"
    _description = __doc__

    original = fields.Many2One('product.template', 'Product Original',
            required=True, ondelete='CASCADE', select=1)
    product = fields.Many2One('product.template', 'Product Analogue',
            required=True, ondelete='CASCADE', select=1)

ProductAnalogue()

class ProductFixedAssets(ModelSQL, ModelView):
    "Product Fixed Assets"
    _name = "product.fixed_assets"
    _description = __doc__
    _inherits = {'product.template': 'template'}

    template = fields.Many2One('product.template', 'Product Template',
            required=True, ondelete='CASCADE', select=1)

    def create(self, vals):
        later = {}
        vals = vals.copy()
        for field in vals:
            if field in self._columns\
                and hasattr(self._columns[field], 'set'):
                    later[field] = vals[field]
        for field in later:
            del vals[field]
        if cursor.nextid(self._table):
            cursor.setnextid(self._table, cursor.currid(self._table))
        new_id = super(ProductFixedAssets, self).create(vals)
        fixed_assets = self.browse(new_id)
        new_id = fixed_assets.template.id
        cursor.execute('UPDATE "' + self._table + '" SET id = %s '\
                        'WHERE id = %s', (fixed_assets.template.id, fixed_assets.id))
        ModelStorage.delete(self, fixed_assets.id)
        self.write(new_id, later)
        res = self.browse(new_id)
        return res.id

ProductFixedAssets()

class ProductIntangibleAssets(ModelSQL, ModelView):
    "Product Intangible Assets"
    _name = "product.intangible_assets"
    _description = __doc__
    _inherits = {'product.template': 'template'}

    template = fields.Many2One('product.template', 'Product Template',
            required=True, ondelete='CASCADE', select=1)

    def create(self, vals):
        later = {}
        vals = vals.copy()
        for field in vals:
            if field in self._columns\
                and hasattr(self._columns[field], 'set'):
                    later[field] = vals[field]
        for field in later:
            del vals[field]
        if cursor.nextid(self._table):
            cursor.setnextid(self._table, cursor.currid(self._table))
        new_id = super(ProductIntangibleAssets, self).create(vals)
        intangible_assets = self.browse(new_id)
        new_id = fixed_assets.template.id
        cursor.execute('UPDATE "' + self._table + '" SET id = %s '\
                        'WHERE id = %s', (intangible_assets.template.id, intangible_assets.id))
        ModelStorage.delete(self, intangible_assets.id)
        self.write(new_id, later)
        res = self.browse(new_id)
        return res.id

ProductIntangibleAssets()

class ProductMaterial(ModelSQL, ModelView):
    "Product Material"
    _name = "product.material"
    _description = __doc__
    _inherits = {'product.template': 'template'}

    template = fields.Many2One('product.template', 'Product Template',
            required=True, ondelete='CASCADE', select=1)

    def create(self, vals):
        later = {}
        vals = vals.copy()
        for field in vals:
            if field in self._columns\
                and hasattr(self._columns[field], 'set'):
                    later[field] = vals[field]
        for field in later:
            del vals[field]
        if cursor.nextid(self._table):
            cursor.setnextid(self._table, cursor.currid(self._table))
        new_id = super(ProductMaterial, self).create(vals)
        material = self.browse(new_id)
        new_id = material.template.id
        cursor.execute('UPDATE "' + self._table + '" SET id = %s '\
                        'WHERE id = %s', (material.template.id, material.id))
        ModelStorage.delete(self, material.id)
        self.write(new_id, later)
        res = self.browse(new_id)
        return res.id

ProductMaterial()

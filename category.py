#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields

class Category(ModelSQL, ModelView):
    "Product Category"
    _name = "product.category"
    _description = __doc__

    name = fields.Char('Name', required=True, translate=True)
    code = fields.Char('Code', size=10)
    parent = fields.Many2One('product.category','Parent', select=1)
    childs = fields.One2Many('product.category', 'parent',
            string='Children')
    type = fields.Selection([
        ('fixed_assets', 'Fixed Assets'),
        ('material', 'Material'),
        ('intangible', 'Intangible assets'),
        ('goods', 'Goods'),
        ('service', 'Service'),
        ('view', 'View'),
        ], 'Type', required=True)

    id_1c = fields.Char("ID import from 1C", size=None, select=1)

    def __init__(self):
        super(Category, self).__init__()
        self._order.insert(0, ('name', 'ASC'))

    def get_rec_name(self, ids, name):
        if not ids:
            return {}
        res = {}
        def _name(category):
            if category.id in res:
                return res[category.id]
            elif category.parent:
                return _name(category.parent) + ' / ' + category.name
            else:
                return category.name
        for category in self.browse(ids):
            res[category.id] = _name(category)
        return res

Category()

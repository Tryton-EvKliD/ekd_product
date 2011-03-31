#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields

class GroupProduct(ModelSQL, ModelView):
    "Product Group"
    _name = "product.group"
    _description = __doc__

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', size=12)
    code_full = fields.Function(fields.Char('Code', size=12), 'get_code_full')
    parent = fields.Many2One('product.group','Parent', select=1)
    childs = fields.One2Many('product.group', 'parent',
            string='Children')
    id_1c = fields.Char("ID import from 1C", size=None, select=1)

    def __init__(self):
        super(GroupProduct, self).__init__()
        self._order.insert(0, ('name', 'ASC'))

    def get_rec_name(self, ids, name):
        if not ids:
            return {}
        res = {}
        def _name(group):
            if group.id in res:
                return res[group.id]
            elif group.parent:
                return _name(group.parent) + ' / ' + group.name
            else:
                return group.name
        for group in self.browse(ids):
            res[group.id] = _name(group)
        return res

    def get_code_full(self, ids, name):
        if not ids:
            return {}
        res = {}
        def _name(group):
            if group.id in res:
                return res[group.id]
            elif group.parent:
                return _name(group.parent) + '.' + group.code
            else:
                return group.code
        for group in self.browse(ids):
            res[group.id] = _name(group)
        return res


GroupProduct()

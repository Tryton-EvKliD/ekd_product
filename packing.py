#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.model.modelstorage import OPERATORS
from trytond.transaction import Transaction
from trytond.pyson import Not, Bool, Eval
from decimal import Decimal

STATES = {
    'readonly': Not(Bool(Eval('active'))),
}

class ProductPacking(ModelSQL, ModelView):
    'Unit of measure Packing'
    _name = 'ekd.product.packing'
    _description = __doc__

    product = fields.Many2One('product.product', 'Product')
    name = fields.Char('Name',  size=None, required=True, states=STATES,
            translate=True)
    symbol = fields.Char('Symbol', size=10, required=True, states=STATES,
            translate=True)
    parent = fields.Many2One('ekd.product.packing', 'Parent packing')
    childs = fields.One2Many('ekd.product.packing', 'parent', 'Child packing')
    rate = fields.Float('Rate', digits=(12, 12), required=True,
            on_change=['rate'], states=STATES,
            help='The coefficient for the formula:\n' \
                    '1 (base unit) = coef (this unit)')
    factor = fields.Float('Factor', digits=(12, 12), states=STATES,
            on_change=['factor'], required=True,
            help='The coefficient for the formula:\n' \
                    'coef (base unit) = 1 (this unit)')
    rounding = fields.Float('Rounding Precision', digits=(12, 12),
            required=True, states=STATES)
    digits = fields.Integer('Display Digits')
    volume = fields.Char('Volume', size=128, help="Length x Width x Height")
    volume_uom = fields.Many2One('product.uom', 'Volume UoM')
    sequence = fields.Integer('Sequence')
    active = fields.Boolean('Active')

    def __init__(self):
        super(ProductPacking, self).__init__()
        self._sql_constraints += [
            ('non_zero_rate_factor', 'CHECK((rate != 0.0) or (factor != 0.0))',
                'Rate and factor can not be both equal to zero.')
        ]
        self._constraints += [
            ('check_factor_and_rate', 'invalid_factor_and_rate'),
        ]
        self._order.insert(0, ('name', 'ASC'))
        self._error_messages.update({
                'change_uom_rate_title': 'You cannot change Rate, Factor or '
                    'Category on a Unit of Measure. ',
                'change_uom_rate': 'If the UOM is still not used, you can '
                    'delete it otherwise you can deactivate it '
                    'and create a new one.',
                'invalid_factor_and_rate': 'Invalid Factor and Rate values!',
            })

    def check_xml_record(self, ids, values):
        return True

    def default_rate(self):
        return 1.0

    def default_factor(self):
        return 1.0

    def default_active(self):
        return 1

    def default_rounding(self):
        return 0.01

    def default_digits(self):
        return 2

    def on_change_factor(self, value):
        if value.get('factor', 0.0) == 0.0:
            return {'rate': 0.0}
        return {'rate': round(1.0 / value['factor'], self.rate.digits[1])}

    def on_change_rate(self, value):
        if value.get('rate', 0.0) == 0.0:
            return {'factor': 0.0}
        return {'factor': round(1.0 / value['rate'], self.factor.digits[1])}

    def search_rec_name(self, name, clause):
        ids = self.search(['OR',
            (self._rec_name,) + clause[1:],
            ('symbol',) + clause[1:],
            ], order=[])
        return [('id', 'in', ids)]

    @staticmethod
    def round(number, precision=1.0):
        return round(number / precision) * precision

    def check_factor_and_rate(self, ids):
        "Check coherence between factor and rate"
        for uom in self.browse(ids):
            if uom.rate == uom.factor == 0.0:
                continue
            if uom.rate != round(1.0 / uom.factor, self.rate.digits[1]) and \
                    uom.factor != round(1.0 / uom.rate, self.factor.digits[1]):
                return False
        return True

    def select_accurate_field(self, uom):
        """
        Select the more accurate field.
        It chooses the field that has the least decimal.

        :param uom: a BrowseRecord of UOM.
        :return: 'factor' or 'rate'.
        """
        lengths = {}
        for field in ('rate', 'factor'):
            format = '%%.%df' % getattr(self, field).digits[1]
            lengths[field] = len((format % getattr(uom,
                field)).split('.')[1].rstrip('0'))
        if lengths['rate'] < lengths['factor']:
            return 'rate'
        elif lengths['factor'] < lengths['rate']:
            return 'factor'
        elif uom.factor >= 1.0:
            return 'factor'
        else:
            return 'rate'

    def compute_qty(self, from_packing, qty, to_packing=None, round=True):
        """
        Convert quantity for given packing's.

        :param from_uom: a BrowseRecord of product.uom
        :param qty: an int or long or float value
        :param to_uom: a BrowseRecord of product.uom
        :param round: a boolean to round or not the result
        :return: the converted quantity
        """
        if not from_packing or not qty or not to_packing:
            return qty
        if from_uom.category.id != to_packing.category.id:
            return qty
        if self.select_accurate_field(from_uom) == 'factor':
            amount = qty * from_uom.factor
        else:
            amount = qty / from_uom.rate
        if to_uom is not None:
            if self.select_accurate_field(to_uom) == 'factor':
                amount = amount / to_uom.factor
            else:
                amount = amount * to_uom.rate
            if round:
                amount = self.round(amount, to_uom.rounding)
        return amount

    def compute_price(self, from_uom, price, to_uom=False,
            context=None):
        """
        Convert price for given uom's.

        :param from_uom: a BrowseRecord of product.uom
        :param price: a Decimal value
        :param to_uom: a BrowseRecord of product.uom
        :return: the converted price
        """
        if not from_uom or not price or not to_uom:
            return price
        if from_uom.category.id != to_uom.category.id:
            return price
        factor_format = '%%.%df' % self.factor.digits[1]
        rate_format = '%%.%df' % self.rate.digits[1]

        if self.select_accurate_field(from_uom) == 'factor':
            new_price = price / Decimal(factor_format % from_uom.factor)
        else:
            new_price = price * Decimal(rate_format % from_uom.rate)

        if self.select_accurate_field(to_uom) == 'factor':
            new_price = new_price * Decimal(factor_format % to_uom.factor)
        else:
            new_price = new_price / Decimal(rate_format % to_uom.rate)

        return new_price

ProductPacking()

class ProductTemplatePacking(ModelSQL, ModelView):
    'Unit of measure Packing Template'
    _name = 'ekd.product.template.packing'
    _description = __doc__

    template = fields.Many2One('ekd.product.template', 'Template product')
    name = fields.Char('Name', size=None, required=True, states=STATES,
            translate=True)
    symbol = fields.Char('Symbol', size=10, required=True, states=STATES,
            translate=True)
    parent = fields.Many2One('ekd.product.packing', 'Parent packing')
    childs = fields.One2Many('ekd.product.packing', 'parent', 'Child packing')
    rate = fields.Float('Rate', digits=(12, 12), required=True,
            on_change=['rate'], states=STATES,
            help='The coefficient for the formula:\n' \
                    '1 (base unit) = coef (this unit)')
    factor = fields.Float('Factor', digits=(12, 12), states=STATES,
            on_change=['factor'], required=True,
            help='The coefficient for the formula:\n' \
                    'coef (base unit) = 1 (this unit)')
    rounding = fields.Float('Rounding Precision', digits=(12, 12),
            required=True, states=STATES)
    volume = fields.Char('Volume Packaging', size=128, help="Length x Width x Height")
    volume_uom = fields.Many2One('product.uom', 'Volume UoM')
    digits = fields.Integer('Display Digits')
    sequence = fields.Integer('Sequence')
    active = fields.Boolean('Active')

    def __init__(self):
        super(ProductTemplatePacking, self).__init__()
        self._sql_constraints += [
            ('non_zero_rate_factor', 'CHECK((rate != 0.0) or (factor != 0.0))',
                'Rate and factor can not be both equal to zero.')
        ]
        self._constraints += [
            ('check_factor_and_rate', 'invalid_factor_and_rate'),
        ]
        self._order.insert(0, ('name', 'ASC'))
        self._error_messages.update({
                'change_uom_rate_title': 'You cannot change Rate, Factor or '
                    'Category on a Unit of Measure. ',
                'change_uom_rate': 'If the UOM is still not used, you can '
                    'delete it otherwise you can deactivate it '
                    'and create a new one.',
                'invalid_factor_and_rate': 'Invalid Factor and Rate values!',
            })

    def check_xml_record(self, ids, values):
        return True

    def default_rate(self):
        return 1.0

    def default_factor(self):
        return 1.0

    def default_active(self):
        return 1

    def default_rounding(self):
        return 0.01

    def default_digits(self):
        return 2

    def on_change_factor(self, value):
        if value.get('factor', 0.0) == 0.0:
            return {'rate': 0.0}
        return {'rate': round(1.0 / value['factor'], self.rate.digits[1])}

    def on_change_rate(self, value):
        if value.get('rate', 0.0) == 0.0:
            return {'factor': 0.0}
        return {'factor': round(1.0 / value['rate'], self.factor.digits[1])}

    def search_rec_name(self, name, clause):
        ids = self.search(['OR',
            (self._rec_name,) + clause[1:],
            ('symbol',) + clause[1:],
            ], order=[])
        return [('id', 'in', ids)]

    @staticmethod
    def round(number, precision=1.0):
        return round(number / precision) * precision

    def check_factor_and_rate(self, ids):
        "Check coherence between factor and rate"
        for uom in self.browse(ids):
            if uom.rate == uom.factor == 0.0:
                continue
            if uom.rate != round(1.0 / uom.factor, self.rate.digits[1]) and \
                    uom.factor != round(1.0 / uom.rate, self.factor.digits[1]):
                return False
        return True

    def select_accurate_field(self, uom):
        """
        Select the more accurate field.
        It chooses the field that has the least decimal.

        :param uom: a BrowseRecord of UOM.
        :return: 'factor' or 'rate'.
        """
        lengths = {}
        for field in ('rate', 'factor'):
            format = '%%.%df' % getattr(self, field).digits[1]
            lengths[field] = len((format % getattr(uom,
                field)).split('.')[1].rstrip('0'))
        if lengths['rate'] < lengths['factor']:
            return 'rate'
        elif lengths['factor'] < lengths['rate']:
            return 'factor'
        elif uom.factor >= 1.0:
            return 'factor'
        else:
            return 'rate'

    def compute_qty(self, from_packing, qty, to_packing=None, round=True):
        """
        Convert quantity for given packing's.

        :param from_uom: a BrowseRecord of product.uom
        :param qty: an int or long or float value
        :param to_uom: a BrowseRecord of product.uom
        :param round: a boolean to round or not the result
        :return: the converted quantity
        """
        if not from_packing or not qty or not to_packing:
            return qty
        if from_uom.category.id != to_packing.category.id:
            return qty
        if self.select_accurate_field(from_uom) == 'factor':
            amount = qty * from_uom.factor
        else:
            amount = qty / from_uom.rate
        if to_uom is not None:
            if self.select_accurate_field(to_uom) == 'factor':
                amount = amount / to_uom.factor
            else:
                amount = amount * to_uom.rate
            if round:
                amount = self.round(amount, to_uom.rounding)
        return amount

    def compute_price(self, from_uom, price, to_uom=False,
            context=None):
        """
        Convert price for given uom's.

        :param from_uom: a BrowseRecord of product.uom
        :param price: a Decimal value
        :param to_uom: a BrowseRecord of product.uom
        :return: the converted price
        """
        if not from_uom or not price or not to_uom:
            return price
        if from_uom.category.id != to_uom.category.id:
            return price
        factor_format = '%%.%df' % self.factor.digits[1]
        rate_format = '%%.%df' % self.rate.digits[1]

        if self.select_accurate_field(from_uom) == 'factor':
            new_price = price / Decimal(factor_format % from_uom.factor)
        else:
            new_price = price * Decimal(rate_format % from_uom.rate)

        if self.select_accurate_field(to_uom) == 'factor':
            new_price = new_price * Decimal(factor_format % to_uom.factor)
        else:
            new_price = new_price / Decimal(rate_format % to_uom.rate)

        return new_price

ProductTemplatePacking()

class ProductTemplatePackingAdd(ModelSQL, ModelView):
    _name = 'ekd.product.template'
    _description = __doc__

    packing = fields.One2Many('ekd.product.template.packing', 'template', 'Packing')

ProductTemplatePackingAdd()

class ProductPackingAdd(ModelSQL, ModelView):
    _name = 'product.template'
    _description = __doc__

    packing = fields.One2Many('ekd.product.packing', 'product', 'Packing')

ProductPackingAdd()
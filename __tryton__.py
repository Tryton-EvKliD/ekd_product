# -*- coding: utf-8 -*-
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
{
    'name' : 'Product',
    'name_de_DE': 'Artikel',
    'name_es_CO': 'Productos',
    'name_es_ES': 'Producto',
    'name_fr_FR': 'Produit',
    'version' : '1.8.0',
    'author' : 'Dmitry Klimanov',
    'email': 'k-dmitry@narod.ru',
    'website': 'http://www.tryton.org/',
    'description': 'Define products, categories of product, units ' \
        'of measure, categories of units of measure.',
    'description_ru_RU': '''
    Словарь товарно-материальных ценностей.
     - Добавление свойств ТМЦ,
     - Добавление шаблона ТМЦ
     - Убирает поля:
        - Цена прихода,
        - Цена продажная, 
        - Метод списания.
    ''',
    'depends' : [
        'ir',
        'res',
        'product',
        'ekd_system',
    ],
    'xml' : [
        'xml/product.xml',
        'xml/product_template.xml',
        'xml/category.xml',
        'xml/category_data.xml',
        'xml/group.xml',
        'xml/group_data.xml',
        'xml/type_value.xml',
#        'xml/uom.xml',
    ],
    'translation': [
        'ru_RU.csv',
    ]
}


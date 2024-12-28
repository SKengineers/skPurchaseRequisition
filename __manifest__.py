# -*- coding: utf-8 -*-
{
    'name': "SK odoo Material Purchase Requisition",
    'summary': """
        Material Purchase Requisition""",
    'description': """
        Material Purchase Requisition
            """,
    'author': 'Sritharan K',
    'company': 'SK Engineer',
    'maintainer': 'SK Engineer',
    'website': "https://www.skengineer.be",
    'category': 'Tools',
    'version': '17.1',
    'depends': ['mail', 'hr', 'stock', 'purchase', 'account'],
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',

        'data/ir_sequence.xml',

        'views/purchase_requisition_view.xml',
        'views/hr_employee_view.xml',
        'views/hr_department_view.xml',

        'wizard/wizard_reject_purchase_requisition_view.xml',
    ],
    'images': [
        '/static/description/icon.png',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}

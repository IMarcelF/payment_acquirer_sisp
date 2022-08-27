# -*- coding: utf-8 -*-
###############################################################################
#
#    Marcel YEKINI
#    Copyright (C) 2022-TODAY Marcel YEKINI (<iekinyfernandes@gmail.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
{
    'name': 'SISP Payment Acquirer | Cape-verdean Payment Gateway Integration',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 380,
    'summary': 'Payment Acquirer: SISP Implementation (Cabo Verde)',
    'version': '1.0',
    'description': """SISP Payment Acquirer: The Cape-verdean Payment Gateway Integration""",
    "author": "MARCEL YEKINI",
    'support': 'iekinyfernandes@gmail.com',
    'website': '#',
    'live_test_url': '#',
    "development_status": "Beta",
    'license': 'LGPL-3',
    'depends': ['payment'],
    'data': [
        'views/payment_templates.xml',
        'views/payment_sisp_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
	'uninstall_hook': 'uninstall_hook',
    'installable': True,
	'application': True,
    'auto_install': False,
}

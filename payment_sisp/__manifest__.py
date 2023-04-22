# -*- coding: utf-8 -*-
###############################################################################
#
#    Marcel YEKINI
#    Copyright (C) 2022 Marcel YEKINI (<iekinyfernandes@gmail.com>).
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
    'category': 'Accounting/Payment Providers',
    'sequence': 380,
    'summary': 'Payment Acquirer: SISP Implementation (Cabo Verde)',
    'version': '1.0',
    'description': """SISP Payment Acquirer: The Cape-verdean Payment Gateway Integration""",
    "author": "MARCEL YEKINI",
    'support': 'iekinyfernandes@gmail.com',
    "images": ["static/description/assets/img/main_screenshot.png"],
    'license': 'LGPL-3',
    'depends': ['payment'],
    'data': [
        'views/payment_sisp_templates.xml',
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',
    ],
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook'
}

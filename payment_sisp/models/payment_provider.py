# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):

    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('sisp', 'SISP')], ondelete={'sisp': 'set default'})

    sisp_pos_id = fields.Char(required_if_provider='sisp', groups='base.group_system', string='POS ID')
    sisp_pos_aut_code = fields.Char(required_if_provider='sisp', groups='base.group_system', string='POS AuthCode')
    sisp_endpoint = fields.Char(required_if_provider='sisp', groups='base.group_system', string='Endpoint')
    sisp_3ds = fields.Boolean(groups='base.group_system', string='3Ds')
    sisp_entity_code = fields.Char(groups='base.group_system', string='Entity Code')

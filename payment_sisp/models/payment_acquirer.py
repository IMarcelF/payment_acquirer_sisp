# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PaymentAcquirer(models.Model):

    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('sisp', 'SISP')], ondelete={'sisp': 'set default'})

    sisp_pos_id = fields.Char(required_if_provider='sisp', groups='base.group_user', string='POS ID')
    sisp_pos_aut_code = fields.Char(required_if_provider='sisp', groups='base.group_user', string='POS AuthCode')
    sisp_endpoint = fields.Char(required_if_provider='sisp', groups='base.group_user', string='Endpoint')
    sisp_3ds = fields.Boolean(groups='base.group_user', string='3Ds')

    @api.model
    def _get_compatible_acquirers(self, *args, is_validation=False, **kwargs):
        acquirers = super()._get_compatible_acquirers(*args, is_validation=is_validation, **kwargs)
        if is_validation:
            acquirers = acquirers.filtered(lambda a: a.provider != 'sisp')
        return acquirers

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'sisp':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_sisp.payment_method_sisp').id

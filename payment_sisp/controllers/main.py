# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import pprint
import werkzeug
import logging


_logger = logging.getLogger(__name__)

class PaymentSispController(http.Controller):

    @http.route('/payment/sisp/response', type='http',  methods=['POST'], auth='public', csrf=False)
    def sisp_response(self, **post):
        _logger.info('SISP: entering form_feedback with post response data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'sisp')
        return werkzeug.utils.redirect('/payment/process')

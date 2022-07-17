# -*- coding: utf-8 -*-

import logging
import pprint
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymentSispController(http.Controller):

    @http.route('/payment/sisp/response', type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def sisp_payment_response(self, **data):
        _logger.info("Received SISP return data:\n%s", pprint.pformat(data))
        request.env['payment.transaction'].sudo()._handle_feedback_data('sisp', data)
        return request.redirect('/payment/status')

# -*- coding: utf-8 -*-

import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SispController(http.Controller):

    _return_url = '/payment/sisp/return'

    @http.route(_return_url, type='http', auth='public', methods=['POST'], csrf=False)
    def sisp_return_from_checkout(self, **raw_data):

        _logger.info("Handling redirection from SISP with data:\n%s", pprint.pformat(raw_data))

        # Check the integrity of the notification
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data('sisp', raw_data)

        # Apply filter if needed

        # Handle the notification data
        tx_sudo._handle_notification_data('sisp', raw_data)

        return request.redirect('/payment/status')

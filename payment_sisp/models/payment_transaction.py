# -*- coding: utf-8 -*-
import logging
import hashlib
import base64
import json

from werkzeug import urls
from datetime import datetime

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_sisp.controllers.main import SispController

_logger = logging.getLogger(__name__)

SUCCESS_MESSAGE_TYPE = ['8', '10', 'P', 'M']


class PaymentTransaction(models.Model):

    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        if provider_code == 'sisp':
            prefix = payment_utils.singularize_reference_prefix()
        return super()._compute_reference(provider_code, prefix=prefix, separator=separator, **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'sisp':
            return res
        current_datetime = datetime.now()
        user_lang = self.env.context.get('lang')
        # Check for supported locales
        if user_lang.startswith('pt_') or user_lang.startswith('en_'):
            user_lang = user_lang.split('_')[0]
        else:
            user_lang = 'en'
        rendering_values = {
            'transactionCode': '1',
            'posID': self.provider_id.sisp_pos_id,
            'merchantRef': self.reference,
            'merchantSession': 'S{}'.format(current_datetime.strftime("%Y%m%d%H%M%S")),
            'amount': round(self.amount),
            'currency': '132',
            'is3DSec': '1',
            'urlMerchantResponse': urls.url_join(self.get_base_url(), SispController._return_url),
            'languageMessages': user_lang,
            'timeStamp': current_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'fingerprintversion': '1',
            'entityCode': '',
            'referenceNumber': '',
        }
        rendering_values['fingerprint'] = self._generate_request_fingerprint(rendering_values)
        query_string = {
            'FingerPrint': rendering_values['fingerprint'],
            'TimeStamp': rendering_values['timeStamp'],
            'FingerPrintVersion': rendering_values['fingerprintversion'],
        }
        rendering_values['api_url'] = '{}?{}'.format(self.provider_id.sisp_endpoint, urls.url_encode(query_string))
        if self.provider_id.sisp_3ds:
            rendering_values['purchaseRequest'] = self._generate_purchase_request()
        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):

        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'sisp' or len(tx) == 1:
            return tx

        user_cancelled, merchant_ref, merchant_resp_merchant_ref = notification_data.get(
            'UserCancelled'), notification_data.get('merchantRef'), notification_data.get('merchantRespMerchantRef')
        reference = None
        if user_cancelled == 'true':
            reference = merchant_ref
        elif merchant_resp_merchant_ref:
            reference = merchant_resp_merchant_ref
        if not reference:
            raise ValidationError('SISP: Referência não encontrada na resposta.')

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'sisp')])
        if not tx:
            raise ValidationError("SISP: " + _("No transaction found matching reference %s.", reference))
        return tx

    def _process_notification_data(self, notification_data):

        super()._process_notification_data(notification_data)
        if self.provider_code != "sisp":
            return

        reason = None
        user_cancelled, merchant_ref, message_type, merchant_resp_merchant_ref = notification_data.get(
            'UserCancelled'), notification_data.get(
            'merchantRef'), notification_data.get('messageType'), notification_data.get('merchantRespMerchantRef')
        if message_type in SUCCESS_MESSAGE_TYPE and merchant_resp_merchant_ref:
            generated_finger_print = self._generate_response_fingerprint(notification_data)
            if generated_finger_print == notification_data.get('resultFingerPrint'):
                self._set_done()
                status = "done"
            else:
                status = "error"
                reason = 'SISP: ' + _('Invalid Response FingerPrint')
                self._set_error(reason)
        elif user_cancelled == 'true' and merchant_ref:
            status = "cancel"
            self._set_canceled()
        else:
            self._set_error('SISP: ' + _("Unrecognized response received from the payment provider."))
            status = "error"
            merchant_resp_error_description, merchant_resp_error_detail = notification_data.get(
                'merchantRespErrorDescription'), notification_data.get('merchantRespErrorDetail')
            if merchant_resp_error_description and merchant_resp_error_detail:
                reason = 'Error Detail: {}. Error Description: {}'.format(merchant_resp_error_detail,
                                                                          merchant_resp_error_description)
        if status == 'error' and reason:
            _logger.info(
                "Received data for transaction with reference %(ref)s, set status as '%(status)s' and error reason as %(reason)s",
                {'ref': self.reference, 'status': status, 'reason': reason})
        else:
            _logger.info("Received data for transaction with reference %(ref)s, set status as '%(status)s'",
                         {'ref': self.reference, 'status': status})

    def _generate_request_fingerprint(self, kwargs):
        to_hash = base64.b64encode(hashlib.sha512(bytes(self.provider_id.sisp_pos_aut_code, "ascii")).digest()).decode("ascii")
        to_hash = '{}{}{}{}{}{}{}{}{}{}'.format(
            to_hash,
            kwargs['timeStamp'],
            int(float(kwargs['amount']) * 1000),
            kwargs['merchantRef'],
            kwargs['merchantSession'],
            kwargs['posID'],
            kwargs['currency'],
            kwargs['transactionCode'],
            kwargs['entityCode'],
            kwargs['referenceNumber'],
        )
        return base64.b64encode(hashlib.sha512(bytes(to_hash, "ascii")).digest()).decode("ascii")

    def _generate_response_fingerprint(self, kwargs):
        to_hash = base64.b64encode(hashlib.sha512(bytes(self.provider_id.sisp_pos_aut_code, "ascii")).digest()).decode(
            "ascii")
        to_hash = '{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}'.format(
            to_hash,
            kwargs['messageType'],
            kwargs['merchantRespCP'],
            kwargs['merchantRespTid'],
            kwargs['merchantRespMerchantRef'],
            kwargs['merchantRespMerchantSession'],
            int(float(kwargs['merchantRespPurchaseAmount']) * 1000),
            kwargs['merchantRespMessageID'],
            kwargs['merchantRespPan'],
            kwargs['merchantResp'],
            kwargs['merchantRespTimeStamp'],
            kwargs['merchantRespReferenceNumber'],
            kwargs['merchantRespEntityCode'],
            kwargs['merchantRespClientReceipt'],
            kwargs['merchantRespAdditionalErrorMessage'].strip(),
            kwargs['merchantRespReloadCode']
        )
        return base64.b64encode(hashlib.sha512(bytes(to_hash, "ascii")).digest()).decode("ascii")

    def _generate_purchase_request(self):
        purchase_request = {
            'acctID': 'x',
            'acctInfo': {
                'chAccAgeInd': '05',
                'chAccChange': self.env.user.write_date.strftime("%Y%m%d"),
                'chAccDate': self.env.user.create_date.strftime("%Y%m%d"),
                'chAccPwChange': self.env.user.write_date.strftime("%Y%m%d"),
                'chAccPwChangeInd': '05',
                'suspiciousAccActivity': '01'
            },

            'email': self.env.user.partner_id.email or None,

            'addrMatch': 'Y',
            'billAddrCity': self.env.user.partner_id.city or None,
            'billAddrCountry': '620',
            'billAddrLine1': self.env.user.partner_id.street or None,
            'billAddrLine2': self.env.user.partner_id.street2 or None,
            'billAddrLine3': self.env.user.partner_id.street2 or None,
            'billAddrPostCode': self.env.user.partner_id.zip or None,
            'billAddrState': self.env.user.partner_id.state_id.code or None,

            'shipAddrCity': self.env.user.partner_id.city or None,
            'shipAddrCountry': '620',
            'shipAddrLine1': self.env.user.partner_id.street or None,
            'shipAddrPostCode': self.env.user.partner_id.zip or None,
            'shipAddrState': self.env.user.partner_id.state_id.code or None,

            'workPhone': {
                'cc': '1',
                'subscriber': self.env.user.partner_id.mobile or None
            },

            'mobilePhone': {
                'cc': '1',
                'subscriber': self.env.user.partner_id.mobile or None
            }
        }
        return base64.b64encode(json.dumps(purchase_request).encode()).decode("ascii")

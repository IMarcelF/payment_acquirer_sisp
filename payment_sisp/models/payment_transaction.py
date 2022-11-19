# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import hashlib
import base64
import json

from odoo import _, api, models
from odoo.exceptions import ValidationError
from werkzeug import urls

_logger = logging.getLogger(__name__)

SUCCESS_MESSAGE_TYPE = ['8', '10', 'P', 'M']


class PaymentTransaction(models.Model):

    _inherit = 'payment.transaction'


    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'sisp':
            return res
        current_datetime = datetime.now()
        sisp_tx_values = {
            'transactionCode': '1',
            'posID': self.acquirer_id.sisp_pos_id,
            'posAutCode': self.acquirer_id.sisp_pos_aut_code,
            'merchantRef': self.reference,
            'merchantSession': 'S{}'.format(current_datetime.strftime("%Y%m%d%H%M%S")),
            'amount': round(processing_values['amount']),
            'sisp_currency': '132',
            'is3DSec': '1',
            'urlMerchantResponse': '{}/payment/sisp/response'.format(self.get_base_url()),
            'languageMessages': 'pt',
            'timeStamp': current_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'fingerprintversion': '1',
            'entityCode': '',
            'referenceNumber': '',
        }
        sisp_tx_values['fingerprint'] = self._generate_request_fingerprint(sisp_tx_values)
        query_string = {
            'FingerPrint': sisp_tx_values['fingerprint'],
            'TimeStamp': sisp_tx_values['timeStamp'],
            'FingerPrintVersion': sisp_tx_values['fingerprintversion'],
        }
        sisp_tx_values['api_url'] = '{}?{}'.format(self.acquirer_id.sisp_endpoint, urls.url_encode(query_string))
        if self.acquirer_id.sisp_3ds:
            sisp_tx_values['purchaseRequest'] = self._generate_purchase_request()
        return sisp_tx_values

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'sisp':
            return tx
        user_cancelled, merchant_ref, merchant_resp_merchant_ref = data.get('UserCancelled'), data.get(
            'merchantRef'), data.get('merchantRespMerchantRef')
        reference = None
        if user_cancelled == 'true':
            reference = merchant_ref
        elif merchant_resp_merchant_ref:
            reference = merchant_resp_merchant_ref
        if not reference:
            raise ValidationError('SISP: Referência não encontrada na resposta.')
        tx = self.search([('reference', '=', reference), ('provider', '=', 'sisp')])
        if not tx:
            raise ValidationError("SISP: Nenhuma transação foi encontrada pela referência %s." % reference)
        return tx

    def _process_feedback_data(self, data):
        super()._process_feedback_data(data)
        if self.provider != "sisp":
            return
        user_cancelled, merchant_ref, message_type, merchant_resp_merchant_ref = data.get('UserCancelled'), data.get(
            'merchantRef'), data.get('messageType'), data.get('merchantRespMerchantRef')
        if message_type in SUCCESS_MESSAGE_TYPE and merchant_resp_merchant_ref:
            generated_finger_print = self._generate_response_fingerprint(data)
            if generated_finger_print == data.get('resultFingerPrint'):
                self._set_done()
            else:
                self._set_error(state_message='SISP: Finger Print de Resposta Inválida.')
        elif user_cancelled == 'true' and merchant_ref:
            self._set_canceled()
        else:
            error = 'SISP: Ocorreu um erro.'
            merchant_resp_error_description, merchant_resp_error_detail = data.get(
                'merchantRespErrorDescription'), data.get('merchantRespErrorDetail')
            if merchant_resp_error_description and merchant_resp_error_detail:
                error = '{} Error Detail: {}. Error Description: {}'.format(error, merchant_resp_error_detail,
                                                                            merchant_resp_error_description)
            self._set_error(state_message=error)

    def _generate_request_fingerprint(self, kwargs):
        to_hash = base64.b64encode(hashlib.sha512(bytes(kwargs['posAutCode'], "ascii")).digest()).decode("ascii")
        to_hash = '{}{}{}{}{}{}{}{}{}{}'.format(
            to_hash,
            kwargs['timeStamp'],
            int(float(kwargs['amount']) * 1000),
            kwargs['merchantRef'],
            kwargs['merchantSession'],
            kwargs['posID'],
            kwargs['sisp_currency'],
            kwargs['transactionCode'],
            kwargs['entityCode'],
            kwargs['referenceNumber'],
        )
        return base64.b64encode(hashlib.sha512(bytes(to_hash, "ascii")).digest()).decode("ascii")

    def _generate_response_fingerprint(self, kwargs):
        to_hash = base64.b64encode(hashlib.sha512(bytes(self.acquirer_id.sisp_pos_aut_code, "ascii")).digest()).decode("ascii")
        to_hash = '{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}'.format(
            to_hash,
            kwargs['messageType'],
            kwargs['merchantRespCP'],
            kwargs['merchantRespTid'],
            kwargs['merchantRespMerchantRef'],
            kwargs['merchantRespMerchantSession'],
            kwargs['merchantRespPurchaseAmount'],
            kwargs['merchantRespMessageID'],
            kwargs['merchantRespPan'],
            kwargs['merchantResp'],
            kwargs['merchantRespTimeStamp'],
            kwargs['merchantRespReferenceNumber'],
            kwargs['merchantRespEntityCode'],
            kwargs['merchantRespClientReceipt'],
            kwargs['merchantRespAdditionalErrorMessage'],
            kwargs['merchantRespReloadCode']
        )
        return base64.b64encode(hashlib.sha512(bytes(to_hash, "ascii")).digest()).decode("ascii")

    def _generate_purchase_request(self):
        purchase_request = {
            'acctID': 'x',
            'acctInfo': {
                'chAccAgeInd': '05',
                'chAccChange':  self.env.user.write_date.strftime("%Y%m%d"),
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

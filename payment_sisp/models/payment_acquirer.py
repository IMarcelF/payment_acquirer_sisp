# coding: utf-8

from datetime import datetime
from odoo import api, exceptions, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from werkzeug import urls
import hashlib
import base64
import logging
import json

_logger = logging.getLogger(__name__)

SUCCESS_MESSAGE_TYPE = ['8', '10', 'P', 'M']


def generate_request_fingerprint(kwargs):
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


def generate_response_fingerprint(kwargs):
    to_hash = base64.b64encode(hashlib.sha512(bytes(kwargs['posAutCode'], "ascii")).digest()).decode("ascii")
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


class PaymentAcquirerSisp(models.Model):

    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('sisp', 'SISP')
    ], ondelete={'sisp': 'set default'})

    sisp_pos_id = fields.Char(required_if_provider='sisp', groups='base.group_user', string='POS ID')
    sisp_pos_aut_code = fields.Char(required_if_provider='sisp', groups='base.group_user', string='POS AuthCode')
    sisp_endpoint = fields.Char(required_if_provider='sisp', groups='base.group_user', string='Endpoint')
    sisp_3ds = fields.Boolean(groups='base.group_user', string='3Ds')

    def sisp_form_generate_values(self, values):
        sisp_tx_values = dict(values)
        current_datetime = datetime.now()
        temp_sisp_tx_values = dict({
            'transactionCode': '1',
            'posID': self.sisp_pos_id,
            'posAutCode': self.sisp_pos_aut_code,
            'merchantRef': values.get('reference'),
            'amount': round(values.get('amount')),
            'merchantSession': 'S{}'.format(current_datetime.strftime("%Y%m%d%H%M%S")),
            'sisp_currency': '132',
            'is3DSec': '1',
            'urlMerchantResponse': '{}payment/sisp/response'.format(self.get_base_url()),
            'languageMessages': 'pt',
            'timeStamp': current_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'fingerprintversion': '1',
            'entityCode': '',
            'referenceNumber': '',
        })
        temp_sisp_tx_values['fingerprint'] = generate_request_fingerprint(temp_sisp_tx_values)
        query_string = {
            'FingerPrint': temp_sisp_tx_values['fingerprint'],
            'TimeStamp': temp_sisp_tx_values['timeStamp'],
            'FingerPrintVersion': temp_sisp_tx_values['fingerprintversion'],
        }
        temp_sisp_tx_values['query_string'] = urls.url_encode(query_string)
        if self.sisp_3ds:
            temp_sisp_tx_values['purchaseRequest'] = self._generate_purchase_request()
        sisp_tx_values.update(temp_sisp_tx_values)
        return sisp_tx_values

    def sisp_get_form_action_url(self):
        self.ensure_one()
        return self.sisp_endpoint

    def _generate_purchase_request(self):
        purchase_request = {
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
            'billAddrLine1': self.env.user.partner_id.street or None,
            'billAddrLine2': self.env.user.partner_id.street2 or None,
            'billAddrLine3': self.env.user.partner_id.street2 or None,
            'billAddrPostCode': self.env.user.partner_id.zip or None,
            'billAddrState': self.env.user.partner_id.state_id.code or None,

            'shipAddrCity': self.env.user.partner_id.city or None,
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


class PaymentTransactionSisp(models.Model):

    _inherit = 'payment.transaction'

    @api.model
    def _sisp_form_get_tx_from_data(self, data):
        user_cancelled, merchant_ref, merchant_resp_merchant_ref = data.get('UserCancelled'), data.get(
            'merchantRef'), data.get('merchantRespMerchantRef')
        reference = None
        if user_cancelled == 'true':
            reference = merchant_ref
        elif merchant_resp_merchant_ref:
            reference = merchant_resp_merchant_ref
        if not reference:
            raise ValidationError('SISP: Referência não encontrada na resposta.')
        transaction = self.search([('reference', '=', reference)])
        if not transaction:
            raise ValidationError('SISP: Nenhuma transação foi encontrada.')
        elif len(transaction) > 1:
            raise ValidationError('SISP: Multiplas transações foram encontradas.')
        return transaction[0]

    def _sisp_form_validate(self, data):
        user_cancelled, merchant_ref, message_type, merchant_resp_merchant_ref = data.get('UserCancelled'), data.get(
            'merchantRef'), data.get('messageType'), data.get('merchantRespMerchantRef')
        if message_type in SUCCESS_MESSAGE_TYPE and merchant_resp_merchant_ref:
            generated_finger_print = generate_response_fingerprint(data)
            if generated_finger_print == data.get('resultFingerPrint'):
                result = self.write({
                    'acquirer_reference': merchant_resp_merchant_ref,
                    'date': fields.Datetime.now(),
                })
                self._set_transaction_done()
                return True
            else:
                self._set_transaction_error('SISP: Finger Print de Resposta Invalida.')
                return False
        elif user_cancelled == 'true' and merchant_ref:
            result = self.write({
                'acquirer_reference': merchant_ref,
                'date': fields.Datetime.now(),
            })
            self._set_transaction_cancel()
            return False
        else:
            error = 'SISP: Ocorreu um erro.'
            merchant_resp_error_description, merchant_resp_error_detail = data.get(
                'merchantRespErrorDescription'), data.get('merchantRespErrorDetail')
            if merchant_resp_error_description and merchant_resp_error_detail:
                error = '{} Error Detail: {}. Error Description: {}'.format(error, merchant_resp_error_detail, merchant_resp_error_description)
            self._set_transaction_error(error)
            return False

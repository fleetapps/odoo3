# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Routes for ECPay redirection and webhook.
PAYMENT_RETURN_ROUTE = '/payment/ecpay/return'
PAYMENT_WEBHOOK_ROUTE = '/payment/ecpay/webhook'

# The currency supported by ECPay, in ISO 4217 format.
SUPPORTED_CURRENCY = 'TWD'

# The codes of the payment methods to activate when ECPay is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'card',
    'wechat_pay',
    '7eleven',
    'bank_transfer',
    'jkopay',
    'twqr',
    # Brand payment methods.
    'visa',
    'mastercard',
    'jcb',
    'unionpay',
}

# Mapping of payment method codes to ECPay codes.
PAYMENT_METHODS_MAPPING = {
    'card': ['Credit', 'ApplePay'],
    'wechat_pay': ['WeiXin'],
    '7eleven': ['CVS', 'BARCODE'],
    'bank_transfer': ['ATM', 'WebATM'],
    'jkopay': ['DigitalPayment'],
    'twqr': ['TWQR'],
}

# Mapping IETF language tags (e.g.: 'fr-BE') to ECPay language codes.
# If a language tag is not listed, the country code prefix can serve as fallback.
LANGUAGE_CODES_MAPPING = {
    'en': 'ENG',
    'ja_JP': 'JPN',
    'ko': 'KOR',
    'zh': 'CHI',
}

# Mapping of transaction states to ECPay success codes.
SUCCESS_CODE_MAPPING = {'done': ('1',), 'pending': ('2', '10100073')}

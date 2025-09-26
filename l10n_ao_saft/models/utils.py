# -*- coding: utf-8 -*-
# from odoo import models
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA1
from decimal import Decimal, ROUND_HALF_UP
import base64
from base64 import b64decode
from xml.dom.minidom import parseString
import unicodedata
import re
# vwith open('/home/crt/hs_private_key.pem', 'r') as f:
# private_key = f.read()
private_key = """-----BEGIN RSA PRIVATE KEY-----
MIICXwIBAAKBgQDFEfemR9u9d7q7RSO4tnU2rkoLULeTRBVsGTjhWw2D8ThRpqzQ
xls0l1fSFQtYz9hxijrn/gZoZYG1aaqbguh5fpLr9YLhgXydByCvvXFZXgTDM2n8
V4hMa5M+ivAbViSVjmHrDjEAbMlgDdBduaawCKFOlMFfp/8RAP+S9RiaPwIDAQAB
AoGBAJtXimtcgW5cjqlH2tyjlsm/oUZCHjLLnEdVqmyZpZG397kFNXxsn0BZfDRx
ujwLuoXlfIGaz9pDCXfDD2T+T9jymK+dyWYd4X9nFqPAJuz2y3AY4BJ6kwe4jew5
V3QMCbMWzvlqdgW9z+OgQUlJ/0hSE3Jz4zM/c/vYK+kc8xuhAkEA7pUZ42LQjSkN
I7xFpK1aFyy8V12ZXV2rQz3Ug91Q0QUtiLQuiYKDdjXDlL7Ysnq1HIqP2Cu75pa8
Fcwekwb3rQJBANN1CdZggfuGD9sJf0CxiZXkQy0UW7WTQg3X6vP3eDjRyb3fm3K+
3CstBpQzOqPSUG1eVtVfoRYSHCDSCxrJxxsCQQC8ZUK/Gt2CSmNUz6vS4Qyd9jZ3
arLbVkcR3vY8dnwFwef15gpFjakPpF7fy2BEd78iXYw+8DH9YRP+xmNySHM1AkEA
i1jxZqiqf8pU4I9doJBejryh2C82UG3+dYj4eFV4kFkPjWSx1+gWxw0g7MDlv9d0
0N3+cxZV3WmJx8cjMkAOSQJBAIW1J3N8wtlwU0Jb8fnUP+xaEsyJk7KOeudXsvFD
Wlbv5cYqT8okF4+32dfVkyFhe/AYpy0qllR2UhA//1ZLQXM=
-----END RSA PRIVATE KEY-----"""

# with open('/home/crt/hs_public_key.pem', 'r') as f:
public_key = ""

def ref_no(name):
    _name = name
    return _name


def gross_total(num):
    our_value = Decimal(num)
    output_value = Decimal(our_value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    return output_value


def signer(content_data):
    rsa_key = RSA.importKey(private_key)
    # print(rsa_key)
    signed = PKCS1_v1_5.new(rsa_key)
    digest = SHA1.new()
    data = base64.b64encode(content_data.encode('ascii'))
    digest.update(b64decode(data))
    return base64.b64encode(signed.sign(digest))


def prepare_xml(xml_obj):
    xml_string = xml_obj.decode('utf-8')
    xml = xml_string.replace('<item>', '').replace('</item>', '')
    xml = xml.replace('<Customers>', '').replace('</Customers>', '')
    xml = xml.replace('<Suppliers>', '').replace('</Suppliers>', '')
    xml = xml.replace('<Journals>', '').replace('</Journals>', '')
    xml = xml.replace('<Products>', '').replace('</Products>', '')
    # xml = xml.replace('<PurchaseInvoices>', '').replace('</PurchaseInvoices>', '')
    xml = xml.replace('<Invoices>', '').replace('</Invoices>', '')
    xml = xml.replace('<Payments>', '').replace('</Payments>', '')
    xml = xml.replace('<Lines>', '').replace('</Lines>', '')
    xml = xml.replace('<Ta>', '').replace('</Ta>', '')
    xml = xml.replace('<WithholdingTa>', '').replace('</WithholdingTa>', '')
    xml = xml.replace('<Descriptio>', '').replace('</Descriptio>', '')


    # xml = xml.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>')
    xml = xml.replace('<AuditFile>',
                      '<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:AO_1.01_01" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:OECD:StandardAuditFile-Tax:AO_1.01_01 https://raw.githubusercontent.com/assoft-portugal/SAF-T-AO/master/XSD/SAFTAO1.01_01.xsd">')

    return parseString(xml).toprettyxml().replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>')


def verify_signer(sin, content_data):
    rsa_key = RSA.importKey(public_key)
    signed = PKCS1_v1_5.new(rsa_key)
    digest = SHA1.new(content_data.encode("utf-8"))
    return signed.verify(digest, sin)


def extract_period(date):
    period = str(date).split('-')
    if period:
        return period[1]
    return 12

def remove_special_chars(text: str) -> str:
    nfkd_form = unicodedata.normalize("NFKD", text)
    without_accents = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", without_accents)
    return cleaned
"""Capability-specific Twilio transport. No automatic outbound access."""
import os
import re
import httpx
try:
    from twilio.request_validator import RequestValidator
except ImportError:
    RequestValidator = None
from .errors import ApplicationError

ADDRESS = re.compile(r'^whatsapp:\+[1-9][0-9]{7,14}$')
SID = re.compile(r'^SM[0-9a-fA-F]{32}$')
STATUSES = {'queued','sending','sent','delivered','read','failed','undelivered'}

def validate_signature(url, params, signature, token):
    if not token or not signature or not signature.isascii(): return False
    if RequestValidator is None:
        return False
    try: return RequestValidator(token).validate(url, params, signature)
    except (TypeError, ValueError): return False

class TwilioTransport:
    def __init__(self, account=None, token=None, sender=None, callback_base=None, transport=None):
        self.account = account or os.getenv('TWILIO_ACCOUNT_SID','')
        self.token = token or os.getenv('TWILIO_AUTH_TOKEN','')
        self.sender = sender or os.getenv('TWILIO_WHATSAPP_FROM','')
        self.callback_base = (callback_base or os.getenv('TWILIO_CALLBACK_BASE_URL','')).rstrip('/')
        self.transport = transport

    @property
    def configured(self):
        return bool(re.fullmatch(r'AC[0-9a-fA-F]{32}',self.account) and self.token and ADDRESS.fullmatch(self.sender))

    async def read_message(self, sid):
        if not self.configured: raise ApplicationError(503,'TWILIO_UNCONFIGURED','Twilio account credentials and sender are not configured.')
        if not SID.fullmatch(sid): raise ApplicationError(422,'MESSAGE_INVALID','Invalid message reference.')
        async with httpx.AsyncClient(transport=self.transport, timeout=15) as client:
            try:
                response = await client.get('https://api.twilio.com/2010-04-01/Accounts/'+self.account+'/Messages/'+sid+'.json', auth=(self.account,self.token))
            except httpx.HTTPError: raise ApplicationError(502,'TWILIO_UNAVAILABLE','Provider message read failed.') from None
        if response.status_code != 200: raise ApplicationError(502,'TWILIO_READ_FAILED','Provider message read was not accepted.')
        data=response.json()
        if data.get('account_sid')!=self.account or data.get('sid')!=sid: raise ApplicationError(502,'ACCOUNT_MISMATCH','Provider message account/reference mismatch.')
        return {k:data.get(k) for k in ('sid','account_sid','from','to','status','error_code','direction')}

    async def send_template(self, recipient, content_sid, variables, *, authorized=False, verified_recipient=False, approved_content=False, status_callback=None):
        # No UI/API calls this method. Review of the exact provider template, recipient and
        # execution mandate is required before a future real dispatcher can use it.
        if not self.configured or not authorized or not verified_recipient or not approved_content:
            raise ApplicationError(422,'TRANSPORT_BLOCKED','Exact template and recipient authority must be verified before test transport.')
        if not ADDRESS.fullmatch(recipient) or not re.fullmatch(r'HX[0-9a-fA-F]{32}', content_sid):
            raise ApplicationError(422,'TEMPLATE_INVALID','A verified WhatsApp recipient and ContentSid are required.')
        from urllib.parse import urlsplit
        if status_callback and (not self.callback_base.startswith('https://') or urlsplit(status_callback).netloc!=urlsplit(self.callback_base).netloc):
            raise ApplicationError(422,'CALLBACK_INVALID','Status callback must use the configured public origin.')
        # New trial supports only provided ContentSid templates; arbitrary variables
        # cannot be claimed to produce approved replenishment text.
        if variables: raise ApplicationError(422,'TEMPLATE_VARIABLES_UNVERIFIED','Trial template variables are not verified.')
        payload={'From':self.sender,'To':recipient,'ContentSid':content_sid}
        if status_callback: payload['StatusCallback']=status_callback
        async with httpx.AsyncClient(transport=self.transport, timeout=15) as client:
            try:
                response=await client.post('https://api.twilio.com/2010-04-01/Accounts/'+self.account+'/Messages.json',auth=(self.account,self.token),data=payload)
            except httpx.HTTPError: return {'status':'unknown','provider_ref':None,'retry_allowed':False}
        if response.status_code>=500: return {'status':'unknown','provider_ref':None,'retry_allowed':False}
        if response.status_code!=201: return {'status':'failed','provider_ref':None,'retry_allowed':False}
        data=response.json()
        if data.get('account_sid')!=self.account or not SID.fullmatch(data.get('sid','')):
            return {'status':'unknown','provider_ref':None,'retry_allowed':False}
        return {'status':'submitted','provider_ref':data['sid'],'retry_allowed':False}

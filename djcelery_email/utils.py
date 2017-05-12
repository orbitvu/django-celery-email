from email.mime.base import MIMEBase

from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMessage


def chunked(iterator, chunksize):
    """
    Yields items from 'iterator' in chunks of size 'chunksize'.

    >>> list(chunked([1, 2, 3, 4, 5], chunksize=2))
    [(1, 2), (3, 4), (5,)]
    """
    chunk = []
    for idx, item in enumerate(iterator, 1):
        chunk.append(item)
        if idx % chunksize == 0:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def email_to_dict(message):
    if isinstance(message, dict):
        return message

    message_dict = {'subject': message.subject,
                    'body': message.body,
                    'from_email': message.from_email,
                    'to': message.to,
                    'bcc': message.bcc,
                    # ignore connection
                    'headers': message.extra_headers,
                    'cc': message.cc}

    if hasattr(message, 'alternatives'):
        message_dict['alternatives'] = message.alternatives
    if message.content_subtype != EmailMessage.content_subtype:
        message_dict["content_subtype"] = message.content_subtype
    if hasattr(message, 'attachments'):
        attachments = []
        for attachment in message.attachments:
            if isinstance(attachment, MIMEBase):
                attachments.append({'class': attachment.__class__.__name__,
                                    'module': attachment.__class__.__module__,
                                    '_headers': attachment._headers,
                                    '_unixfrom': attachment._unixfrom,
                                    '_payload': attachment._payload,
                                    '_charset': attachment._charset,
                                    'preamble': attachment.preamble,
                                    'defects': attachment.defects,
                                    '_default_type': attachment._default_type})
            else:
                attachments.append({'class': 'tuple',
                                    'data': attachment})
        message_dict['attachments'] = attachments
    return message_dict


def dict_to_email(messagedict):
    if isinstance(messagedict, dict) and "content_subtype" in messagedict:
        content_subtype = messagedict["content_subtype"]
        del messagedict["content_subtype"]
    else:
        content_subtype = None

    attachments = messagedict.get('attachments')
    if 'attachments' in messagedict:
        del messagedict['attachments']

    if hasattr(messagedict, 'from_email'):
        ret = messagedict
    elif 'alternatives' in messagedict:
        ret = EmailMultiAlternatives(**messagedict)
    else:
        ret = EmailMessage(**messagedict)

    for attachment in attachments:
        if attachment['class'] == 'tuple':
            ret.attach(*attachment['data'])
        else:
            Klass = getattr(
                __import__(
                    attachment['module'],
                    globals(),
                    locals(),
                    [attachment['class']]),
                attachment['class'])
            attachment_obj = Klass(attachment['_payload'], 'dummysubtype')
            attachment_obj._headers = attachment['_headers']
            attachment_obj._unixfrom = attachment['_unixfrom']
            attachment_obj._payload = attachment['_payload']
            attachment_obj._charset = attachment['_charset']
            attachment_obj.preamble = attachment['preamble']
            attachment_obj.defects = attachment['defects']
            attachment_obj._default_type = attachment['_default_type']
            ret.attach(attachment_obj)

    if content_subtype:
        ret.content_subtype = content_subtype
        messagedict["content_subtype"] = content_subtype  # bring back content subtype for 'retry'

    if attachments:
        messagedict["attachments"] = attachments  # bring back attachments for 'retry'
    return ret

# -*- coding: utf-8 -*-

from imaplib import IMAP4_SSL
from smtplib import SMTP_SSL
from email.mime.text import MIMEText
import email

class Mail:

    def __init__(self, subject, message, recipient, sender=None, uid=None):
        self.subject = subject
        self.message = message
        self.sender = sender
        self.recipient = recipient
        self.uid = uid

    def __str__(self):
        return '<{}>'.format(','.join((self.subject, self.message, self.recipient,\
            self.sender, str(self.uid))))


class MailManager:

    def __init__(self, imap_host=None, imap_port=993, smtp_host=None, smtp_port=465):
        self._imap = None
        self._smtp = None
        self._user = None
        if imap_host:
            self._imap = IMAP4_SSL(imap_host, imap_port)
        if smtp_host:
            self._smtp = SMTP_SSL(smtp_host, smtp_port)

    def authorize(self, user, password):
        self._user = user
        if self._imap:
            self._imap.login(user, password)
        if self._smtp:
            self._smtp.login(user, password)

    def revoke_auth(self):
        if self._imap:
            self._imap.close()
        if self._smtp:
            self._smtp.close()

    def send(self, mail):
        mail.sender = self._user
        self._check_mail(mail)
        mime_text = MIMEText(mail.message, 'plain', 'utf-8')
        mime_text['From'] = mail.sender
        mime_text['To'] = mail.recipient
        mime_text['Subject'] = mail.subject
        self._smtp.sendmail(mail.sender, [mail.recipient], mime_text.as_string())

    # def receive(self, criteria):
    #     '''deprecated.
    #     '''
    #     emails = []
    #     self._imap.select()
    #     # TODO make criteria take effect
    #     typ, uids = self._imap.search('utf-8', criteria)
    #     for uid in uids[0].split():
    #         typ, data = self._imap.fetch(uid, '(RFC822)')
    #         mime_message = email.message_from_bytes(data[0][1])
    #         sender = email.utils.parseaddr(mime_message.get('from'))[1]
    #         recipient = email.utils.parseaddr(mime_message.get('to'))[1]
    #         subject = self._get_subject(mime_message)
    #         message = self._get_message(mime_message)
    #         emails.append(Mail(subject, message, recipient, sender, uid))
    #     return emails

    def pop(self, sender_matcher, subject_matcher):
        mail = None
        self._imap.select()
        _, uids = self._imap.search(None, 'ALL')
        for uid in uids[0].split():
            tmp = self._fetch_mail(uid)
            if tmp.subject == subject_matcher and tmp.sender == sender_matcher:
                mail = tmp
                self.delete(mail.uid)
                break
        return mail

    def _fetch_mail(self, uid):
        _, data = self._imap.fetch(uid, '(RFC822)')
        mime_message = email.message_from_bytes(data[0][1])
        sender = email.utils.parseaddr(mime_message.get('from'))[1]
        recipient = email.utils.parseaddr(mime_message.get('to'))[1]
        subject = self._get_subject(mime_message)
        message = self._get_message(mime_message)
        return Mail(subject, message, recipient, sender, uid)

    def delete(self, uid):
        '''deprecated. do not use this function cause it make uid in confusion.
        '''
        self._imap.store(uid, '+FLAGS', '\\Deleted')
        self._imap.expunge()

    def _get_message(self, mime_message):
        target = None
        if self._is_plain_text_content(mime_message):
            target = mime_message
        else:
            for part in mime_message.get_payload():
                if self._is_plain_text_content(part):
                    target = part
                    continue
        return target.get_payload(decode=True).strip().decode(target.get_content_charset())

    def _is_plain_text_content(self, content):
        return content.get_content_type() == 'text/plain'

    def _get_subject(self, mime_message):
        raw, encoding = email.header.decode_header(mime_message.get('Subject'))[0]
        return raw if not encoding else raw.decode(encoding)

    def _check_mail(self, mail):
        if not mail.sender:
            raise Exception('sender is not set!')
        if not mail.recipient:
            raise Exception('recipient is not set!')

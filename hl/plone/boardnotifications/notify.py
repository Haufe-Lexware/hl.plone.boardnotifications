import logging
import formatter
import StringIO
from lxml import html
from htmllib import HTMLParser
from persistent import Persistent
from persistent.mapping import PersistentMapping
from zope.component import adapts, getUtility, queryUtility
from zope.formlib.form import FormFields
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFDefault.formlib.schema import SchemaAdapterBase
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.CMFPlone.utils import safe_unicode
from zope.interface import implements
from plone.app.controlpanel.form import ControlPanelForm
from Products.MailHost.interfaces import IMailHost
from email.parser import HeaderParser
from email.mime.text import MIMEText
from .interfaces import INotifierSchema, INotifier, ISubscriptions
from zope.i18nmessageid import MessageFactory
_ = MessageFactory('hl.plone.boardnotifications')

log = logging.getLogger('hl.plone.boardnotifications.notify')


class NotifierControlPanelAdapter(SchemaAdapterBase):

    adapts(IPloneSiteRoot)
    implements(INotifierSchema)

    def get_subject(self):
        util = queryUtility(INotifier)
        return getattr(util, 'subject', '')

    def set_subject(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.subject = value

    subject = property(get_subject, set_subject)

    def get_signature(self):
        util = queryUtility(INotifier)
        return getattr(util, 'signature', '')

    def set_signature(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.signature = value

    signature = property(get_signature, set_signature)

    def get_salutations(self):
        util = queryUtility(INotifier)
        salutations = getattr(util, 'salutations', '')
        if salutations:
            salutations = '\n'.join([':'.join(item) for item in salutations.items()])
        return salutations

    def set_salutations(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            di = {}
            if value in (None, ''):
                di[''] = ''
            else:
                di.update([kv.split(':') for kv in value.split('\n')])
            util.salutations = di

    salutations = property(get_salutations, set_salutations)

    def get_comment_edited_text(self):
        util = queryUtility(INotifier)
        return getattr(util, 'comment_edited_text', '')

    def set_comment_edited_text(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.comment_edited_text = value

    comment_edited_text = property(get_comment_edited_text, set_comment_edited_text)

    def get_thread_moved_text(self):
        util = queryUtility(INotifier)
        return getattr(util, 'thread_moved_text', '')

    def set_thread_moved_text(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.thread_moved_text = value

    thread_moved_text = property(get_thread_moved_text, set_thread_moved_text)

    def get_comment_deleted_text(self):
        util = queryUtility(INotifier)
        return getattr(util, 'comment_deleted_text', '')

    def set_comment_deleted_text(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.comment_deleted_text = value

    comment_deleted_text = property(get_comment_deleted_text, set_comment_deleted_text)

    def get_subscription_comment_added_text(self):
        util = queryUtility(INotifier)
        return getattr(util, 'subscription_comment_added_text', u'')

    def set_subscription_comment_added_text(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.subscription_comment_added_text = value

    subscription_comment_added_text = property(get_subscription_comment_added_text, set_subscription_comment_added_text)

    def get_subscription_comment_edited_text(self):
        util = queryUtility(INotifier)
        return getattr(util, 'subscription_comment_edited_text', '')

    def set_subscription_comment_edited_text(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.subscription_comment_edited_text = value

    subscription_comment_edited_text = property(get_subscription_comment_edited_text, set_subscription_comment_edited_text)

    def get_subscription_thread_moved_text(self):
        util = queryUtility(INotifier)
        return getattr(util, 'subscription_thread_moved_text', '')

    def set_subscription_thread_moved_text(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.subscription_thread_moved_text = value

    subscription_thread_moved_text = property(get_subscription_thread_moved_text, set_subscription_thread_moved_text)

    def get_mailin_enabled(self):
        util = queryUtility(INotifier)
        return getattr(util, 'mailin_enabled', '')

    def set_mailin_enabled(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.mailin_enabled = value

    mailin_enabled = property(get_mailin_enabled, set_mailin_enabled)

    def get_fake_manager(self):
        util = queryUtility(INotifier)
        return getattr(util, 'fake_manager', '')

    def set_fake_manager(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.fake_manager = value

    fake_manager = property(get_fake_manager, set_fake_manager)

    def get_listen_addresses(self):
        util = queryUtility(INotifier)
        return getattr(util, 'listen_addresses', '')

    def set_listen_addresses(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.listen_addresses = value

    listen_addresses = property(get_listen_addresses, set_listen_addresses)

    def get_add_attachments(self):
        util = queryUtility(INotifier)
        return getattr(util, 'add_attachments', '')

    def set_add_attachments(self, value):
        util = queryUtility(INotifier)
        if util is not None:
            util.add_attachments = value

    add_attachments = property(get_add_attachments, set_add_attachments)


class NotifierControlPanel(ControlPanelForm):

    form_fields = FormFields(INotifierSchema)

    label = _(u'Settings for board notification mails')
    description = _(u'Here you can configure the mail texts for mails that are '
            'sent out to creators or subscribers of board content when it '
            'changes. You can use the following keywords to replace them using '
            'content coming from the thread: %(threadtitle)s, %(threadurl)s, '
            '%(boardtitle)s, %(mailsignature)s, %(salutation)s and, when '
            'appropriate, %(commenturl)s and %(commenttext)s.')
    form_name = u' Notifier Settings'

    def updateWidgets(self):
        super(NotifierControlPanel, self).updateWidgets()
        self.widgets['subject'].size = 30


class Notifier(Persistent):

    implements(INotifier)

    valid_headers = ('Subject', 'From', 'To')

    def __init__(self):
        self.subject = None
        self.signature = None
        self.comment_edited_text = None
        self.comment_deleted_text = None
        self.subscription_comment_added_text = None
        self.subscription_comment_edited_text = None
        self.thread_moved_text = None
        self._salutations = PersistentMapping()

    def create_plaintext_message(self, text):
        """ Create a plain-text-message by parsing the html
            and attaching links as endnotes

            Modified from EasyNewsletter/content/ENLIssue.py
        """
        # This reflows text which we don't want, but it creates
        # parser.anchorlist which we do want.
        textout = StringIO.StringIO()
        formtext = formatter.AbstractFormatter(formatter.DumbWriter(textout))
        parser = HTMLParser(formtext)
        parser.feed(text)
        parser.close()

        # append the anchorlist at the bottom of a message
        # to keep the message readable.
        counter = 0
        anchorlist = "\n\n" + '----' + "\n\n"
        for item in parser.anchorlist:
            counter += 1
            anchorlist += "[%d] %s\n" % (counter, item)

        # This reflows text:
        # text = textout.getvalue() + anchorlist
        # This just strips tags, no reflow
        text = html.fromstring(text).text_content()
        text += anchorlist
        del textout, formtext, parser, anchorlist
        return text

    def get_salutations(self):
        return self._salutations

    def set_salutations(self, mapping):
        if isinstance(mapping, PersistentMapping):
            self._salutations = mapping
        else:
            self._salutations = PersistentMapping()
            self._salutations.update(mapping)

    salutations = property(get_salutations, set_salutations)

    def _salutation_for_member(self, mdata):
        """
        answer an appropriate salutation
        """
        key = mdata.get('salutation', '')
        return self.salutations.get(key, '') % mdata

    @staticmethod
    def _encoding():
        return getUtility(ISiteRoot).getProperty('email_charset', 'utf-8')

    def _notify(self, mdata, text):
        to_email = mdata.get('email')
        if not to_email:
            log.info('Cannot send notification e-mail because there\'s no destination.')
            return

        headers = {}
        headers.update([tp for tp in HeaderParser().parsestr(text.encode(self._encoding())).items() if tp[0] in self.valid_headers])
        if headers.keys():
            text = '\n\n'.join(text.split('\n\n')[1:])
        text = self.create_plaintext_message(text)
        msg = MIMEText(text, _charset=self._encoding())
        msg['Subject'] = self.subject
        msg['From'] = getUtility(ISiteRoot).email_from_address
        msg['To'] = to_email
        for k, v in headers.items():
            msg.replace_header(k, v)
        mh = getUtility(IMailHost)
        mh.send(msg)

    def _thread_info(self, thread):
        di = {}
        di['threadtitle'] = thread.Title().decode(self._encoding())
        di['threadurl'] = thread.absolute_url()
        di['boardtitle'] = thread.getForum().Title().decode(self._encoding())
        di['mailsignature'] = self.signature
        return di

    @classmethod
    def _memberdata_for_content(cls, content):
        return cls._memberdata_for(content.Creator())

    @classmethod
    def _memberdata_for(cls, memberid):
        site = getUtility(ISiteRoot)
        mtool = getToolByName(site, 'portal_membership')
        mdtool = getToolByName(site, 'portal_memberdata')
        keys = mdtool.propertyIds()
        mdata = mtool.getMemberById(memberid)
        if mdata is None: # no memberdata, most likely the user has been deleted
            return
        result = {}
        result.update([(k, str(mdata.getProperty(k)).decode(cls._encoding())) for k in keys])
        return result

    def _notify_thread_subscribers(self, thread, notification_text, comment=None):
        forum = thread.getForum()
        di = self._thread_info(thread)
        if comment is not None:
            di['commenturl'] = comment.absolute_url()
            di['commenttext'] = safe_unicode(comment.getText())
        subscriptions = getUtility(ISubscriptions)
        subscribers = set(subscriptions.subscribers_for(thread)) | set(subscriptions.subscribers_for(forum))
        mdtool = getToolByName(thread, 'portal_memberdata')
        keys = mdtool.propertyIds()
        for mdata in subscribers:
            if (comment is not None) and (mdata.getId() == comment.Creator()):
                continue
            di.update([(k, str(mdata.getProperty(k)).decode(self._encoding())) for k in keys])
            di['salutation'] = self._salutation_for_member(di)
            self._notify(di, notification_text % di)
            log.info('notified subscriber {subscriber}'.format(subscriber=di.get('email')))

    def comment_edited(self, comment):
        """
        A comment has been edited. Notify the creator of the comment.
        """
        # do not notify the creator if she has edited the comment herself
        mtool = getToolByName(comment, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        creator = mtool.getMemberById(comment.Creator())
        if (member == creator) or creator is None or not self.comment_edited_text or not self.comment_edited_text.strip():
            return
        thread = comment.getConversation()
        di = self._thread_info(thread)
        di.update(self._memberdata_for_content(comment))
        di['salutation'] = self._salutation_for_member(di)
        di['commenturl'] = comment.absolute_url()
        di['commenttext'] = safe_unicode(comment.getText())
        self._notify(di, self.comment_edited_text % di)
        log.info('comment %s has been edited, notified owner %s' % (di['commenturl'], di.get('email')))

    def thread_moved(self, thread):
        """
        A thread has been moved to a new board. Notify all contributors.
        """
        if not self.thread_moved_text or not self.thread_moved_text.strip():
            return
        di = self._thread_info(thread)
        memberids = set([comment.Creator() for comment in thread.getComments()])
        for memberid in memberids:
            md = self._memberdata_for(memberid)
            if md is None:
                log.info('member with id %s could not be found, unable to send notification for %s' % (memberid, di['threadurl']))
                continue
            di.update(md)
            di['salutation'] = self._salutation_for_member(di)
            self._notify(di, self.thread_moved_text % di)
            log.info('thread %s has been moved, notified contributor %s' % (di['threadurl'], di.get('email')))

    def comment_deleted(self, comment):
        """
        A comment has been deleted. Notify its creator.
        """
        if not self.comment_deleted_text or not self.comment_deleted_text.strip():
            return
        thread = comment.getConversation()
        di = self._thread_info(thread)
        di['commenturl'] = comment.absolute_url()
        di['commenttext'] = safe_unicode(comment.getText())
        md = self._memberdata_for_content(comment)
        if md is None:
            log.info('member with id %s could not be found, unable to send notification for %s' % (comment.Creator(), di['commenturl']))
            return
        di.update(self._memberdata_for_content(comment))
        di['salutation'] = self._salutation_for_member(di)
        self._notify(di, self.comment_deleted_text % di)
        log.info('comment %s has been deleted, notified owner %s' % (di['commenturl'], di.get('email')))

    def subscription_comment_edited(self, comment):
        """
        A comment has been edited. Notify thread subscribers.
        """
        if not self.subscription_comment_edited_text or not self.subscription_comment_edited_text.strip():
            return
        thread = comment.getConversation()
        log.info('comment {url} has been edited'.format(url=comment.absolute_url()))
        self._notify_thread_subscribers(thread, self.subscription_comment_edited_text, comment)

    def subscription_comment_added(self, comment):
        """
        A comment has been added to a thread. Notify thread subscribers.
        """
        if not self.subscription_comment_added_text or not self.subscription_comment_added_text.strip():
            return
        thread = comment.getConversation()
        log.info('comment {url} has been edited'.format(url=comment.absolute_url()))
        self._notify_thread_subscribers(thread, self.subscription_comment_added_text, comment)

    def subscription_thread_moved(self, thread):
        """
        A thread has been moved to another forum. Notify thread subscribers.
        """
        if not self.subscription_thread_moved_text or not self.subscription_thread_moved_text.strip():
            return
        log.info('thread {url} has been edited'.format(url=thread.absolute_url()))
        self._notify_thread_subscribers(thread, self.subscription_thread_moved_text)

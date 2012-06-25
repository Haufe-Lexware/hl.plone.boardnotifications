import logging
from persistent import Persistent
from persistent.mapping import PersistentMapping
from zope.component import adapts, getUtility, queryUtility
from zope.formlib.form import FormFields
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFDefault.formlib.schema import SchemaAdapterBase
from Products.CMFPlone.interfaces import IPloneSiteRoot
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
        return getattr(util, 'subscription_comment_added_text', '')

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
 


class NotifierControlPanel(ControlPanelForm):

    form_fields = FormFields(INotifierSchema)

    label = _(u'Settings for board notification mails')
    description = _(u'Here you can configure the mail texts for mails that are send out to creators on subscribers of board content when it changes')
    form_name = u' Notifier Settings'


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
        headers = {}
        headers.update([tp for tp in HeaderParser().parsestr(text.encode(self._encoding())).items() if tp[0] in self.valid_headers])
        if headers.keys():
            text = '\n\n'.join(text.split('\n\n')[1:])
        msg = MIMEText(text, _charset=self._encoding())
        msg['Subject'] = self.subject
        msg['From'] = getUtility(ISiteRoot).email_from_address
        msg['To'] = mdata.get('email')
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
        result = {}
        result.update([(k, str(mdata.getProperty(k)).decode(cls._encoding())) for k in keys])
        return result

    def comment_edited(self, comment):
        """
        a comment has been edited. Notify the creator of the comment.
        """
        # do not notify the creator if she has edited the comment herself
        mtool = getToolByName(comment, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        creator = mtool.getMemberById(comment.Creator())
        if (member == creator) or not self.comment_edited_text:
            return
        thread = comment.getConversation()
        di = self._thread_info(thread)
        di.update(self._memberdata_for_content(comment))
        di['salutation'] = self._salutation_for_member(di)
        di['commenturl'] = comment.absolute_url()
        self._notify(di, self.comment_edited_text % di)
        log.info('comment %s has been edited, notified owner %s' % (di['commenturl'], di.get('email')))

    def thread_moved(self, thread):
        """
        a thread has been moved to a new board. Notify all contributors.
        """
        if not self.thread_moved_text:
            return
        di = self._thread_info(thread)
        memberids = set([comment.Creator() for comment in thread.getComments()])
        for memberid in memberids:
            di.update(self._memberdata_for(memberid))
            di['salutation'] = self._salutation_for_member(di)
            self._notify(di, self.thread_moved_text % di)
            log.info('thread %s has been moved, notified contributor %s' % (di['threadurl'], di.get('email')))

    def comment_deleted(self, comment):
        """
        a comment has been deleted. Notify its creator.
        """
        if not self.comment_deleted_text:
            return
        thread = comment.getConversation()
        di = self._thread_info(thread)
        di.update(self._memberdata_for_content(comment))
        di['salutation'] = self._salutation_for_member(di)
        di['commenturl'] = comment.absolute_url()
        self._notify(di, self.comment_deleted_text % di)
        log.info('comment %s has been deleted, notified owner %s' % (di['commenturl'], di.get('email')))

    def subscription_comment_edited(self, comment):
        """
        a comment has been edited. Notify thread subsribers.
        """
        if not self.subscription_comment_edited_text:
            return
        thread = comment.getConversation()
        di = self._thread_info(thread)
        di['commenturl'] = comment.absolute_url()
        subscriptions = getUtility(ISubscriptions)
        subscribers = subscriptions.subscribers_for(thread)
        mdtool = getToolByName(comment, 'portal_memberdata')
        keys = mdtool.propertyIds()
        for mdata in subscribers:
            if mdata.getId() == comment.Creator():
                continue
            di.update([(k, str(mdata.getProperty(k)).decode(self._encoding())) for k in keys])
            di['salutation'] = self._salutation_for_member(di)
            self._notify(di, self.subscription_comment_edited_text % di)
            log.info('comment %s has been edited, notified subscriber %s' % (di['commenturl'], di.get('email')))

    def subscription_comment_added(self, comment):
        """
        a comment has been added to a thread. Notify thread subscribers.
        """
        if not self.subscription_comment_added_text:
            return
        thread = comment.getConversation()
        di = self._thread_info(thread)
        di['commenturl'] = comment.absolute_url()
        subscriptions = getUtility(ISubscriptions)
        subscribers = subscriptions.subscribers_for(thread)
        mdtool = getToolByName(comment, 'portal_memberdata')
        keys = mdtool.propertyIds()
        for mdata in subscribers:
            if mdata.getId() == comment.Creator():
                continue
            di.update([(k, str(mdata.getProperty(k)).decode(self._encoding())) for k in keys])
            di['salutation'] = self._salutation_for_member(di)
            self._notify(di, self.subscription_comment_added_text % di)
            log.info('comment %s has been added, notified subscriber %s' % (di['commenturl'], di.get('email')))


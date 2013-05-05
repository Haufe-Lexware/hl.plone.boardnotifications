from zope.component import getUtility
from hl.plone.boardnotifications.interfaces import ISubscriptions
from Products import Five
from Products.CMFCore.utils import getToolByName
from plone.app.layout.viewlets.common import ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import re
import email
import urlparse

class Subscribe(Five.BrowserView):

    def __call__(self):
        mtool = getToolByName(self.context, 'portal_membership')
        subscriptions = getUtility(ISubscriptions)
        mem = mtool.getAuthenticatedMember().getId()
        subscriptions.add(self.context, mem)
        self.request.response.redirect(self.context.absolute_url() + '#subscribe')


class Unsubscribe(Five.BrowserView):

    def __call__(self):
        mtool = getToolByName(self.context, 'portal_membership')
        subscriptions = getUtility(ISubscriptions)
        mem = mtool.getAuthenticatedMember().getId()
        subscriptions.remove(self.context, mem)
        self.request.response.redirect(self.context.absolute_url() + '#subscribe')


class SubscriptionViewlet(ViewletBase):

    index = ViewPageTemplateFile('subscribe.pt')

    def is_subscribed_to_forum(self):
        subscriptions = getUtility(ISubscriptions)
        if self.context.portal_type == 'PloneboardForum':
            forum = self.context
        else:
            thread = self.context.getConversation(self.context.id)
            forum = thread.getForum()
        return subscriptions.check_subscriber(forum)

    def is_subscribed(self):
        subscriptions = getUtility(ISubscriptions)
        return subscriptions.check_subscriber(self.context)

class MailIn(Five.BrowserView):

    def __call__(self):
        mailstr = self.request.get('Mail')
        if not mailstr:
            return
        mtool = getToolByName(self.context, 'portal_membership')
        msg = email.message_from_string(mailstr)
        msg_from = msg['From']
        member = mtool.searchMembers('email', msg_from)
        if not member:
            return
        body = msg.get_payload(decode=True)
        if not body:
            # e.g. multipart ...
            return
        # grabbed from http://stackoverflow.com/questions/4696418/regex-to-extract-all-urls-from-a-page
        subj = msg['Subject']
        url_re = re.compile(r'\b(([\w-]+://?|www[.])[^\s()<>]+(?:\([\w\d]+\)|([^[:punct:]\s]|/)))')
        target = None
        for match in url_re.finditer(body):
            url = match.group(0)
            path = urlparse.urlparse(url).path
            obj = self.context.restrictedTraverse(path)
            if obj.meta_type in ['PloneboardComment',
                    'PloneboardConversation']:
                if target is None:
                    target = obj
                elif (obj.meta_type == 'PloneboardComment' and
                        target.meta_type 'PloneboardConversation'):
                    # More specific wins
                    target = obj
            if not target:
                return
            if target.meta_type == 'PloneboardConversation':
                target.addComment('answer via mail'+subj, body, creator=member)
            elif target.meta_type == 'PloneboardComment':
                target.addReply('answer via mail'+subj, body, creator=member)

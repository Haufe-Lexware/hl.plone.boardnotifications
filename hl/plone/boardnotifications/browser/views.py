from zope.component import getUtility
from hl.plone.boardnotifications.interfaces import ISubscriptions
from Products import Five
from Products.CMFCore.utils import getToolByName
from plone.app.layout.viewlets.common import ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

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

    def is_subscribed(self):
        subscriptions = getUtility(ISubscriptions)
        return subscriptions.check_subscriber(self.context)

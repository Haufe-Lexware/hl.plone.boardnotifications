import unittest
import transaction
from Testing import ZopeTestCase
from zope.component import getGlobalSiteManager
from Products.CMFCore.interfaces import ISiteRoot
from mocks import MembershipToolMock, ForumMock, ConversationMock, MemberDataMock


class SubscriptionTests(unittest.TestCase):

    def _make_one(self):
        from hl.plone.boardnotifications.subscribe import Subscriptions
        from hl.plone.boardnotifications.interfaces import ISubscriptions
        subscriptions = Subscriptions()
        getGlobalSiteManager().registerUtility(subscriptions, ISubscriptions)
        return subscriptions

    def setUp(self):
        transaction.begin()
        self.app = ZopeTestCase.app()
        gsm = getGlobalSiteManager()
        gsm.registerUtility(self.app, ISiteRoot)
        self.app.email_from_address = 'forum@lexware.de'
        mtool = MembershipToolMock()
        member = MemberDataMock(id='123456',
                                email='max.mustermann@haufe-lexware.com',
                                salutation='Herr',
                                lastname='Mustermann',
                                firstname='Max')
        mtool.members[member['id']] = member
        self.app._setObject(mtool.id, mtool)
        forum = ForumMock('testforum', 'test forum')
        thread = ConversationMock(id='testthread',
                                  title='test thread',
                                  forum=forum,
                                  creator=member['id'])
        forum._setObject(thread.id, thread)
        self.app._setObject(forum.id, forum)

    def test_subscribers_for(self):
        subscriptions = self._make_one()
        thread = self.app.testforum.testthread
        subscriptions.add(thread, '123456')
        subscriptions.add(thread, '999999') # users that do not exist should be eliminated
        got = subscriptions.subscribers_for(thread)
        self.failUnless(len(got) == 1, 'expected one subscriber')
        email = got[0].getProperty('email')
        self.failUnless(email == 'max.mustermann@haufe-lexware.com', 'wrong memberdata %s' % got[0])


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(SubscriptionTests),
        ))

if __name__ == '__main__':
    from Products.GenericSetup.testing import run
    run(test_suite())

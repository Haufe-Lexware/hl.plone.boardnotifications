import os
import unittest
import ZODB
from ZODB.POSException import ConflictError
import transaction
from Testing import ZopeTestCase
from zope.component import getGlobalSiteManager
from zope.interface.verify import verifyObject
from zope.lifecycleevent import ObjectMovedEvent
from Products.CMFCore.interfaces import ISiteRoot
from mocks import MembershipToolMock, ForumMock, ConversationMock, MemberDataMock, ContentMock
from hl.plone.boardnotifications.interfaces import ISubscriptions


class SubscriptionTests(unittest.TestCase):

    def _make_one(self):
        from hl.plone.boardnotifications.subscribe import Subscriptions
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

    def test_interface(self):
        verifyObject(ISubscriptions, self._make_one())

    def test_subscribers_for(self):
        subscriptions = self._make_one()
        thread = self.app.testforum.testthread
        subscriptions.add(thread, '123456')
        subscriptions.add(thread, '999999') # users that do not exist should be eliminated
        got = subscriptions.subscribers_for(thread)
        self.failUnless(len(got) == 1, 'expected one subscriber')
        email = got[0].getProperty('email')
        self.failUnless(email == 'max.mustermann@haufe-lexware.com', 'wrong memberdata %s' % got[0])

    def test_move_subscriptions(self):
        subscriptions = self._make_one()
        forum = ForumMock('anotherforum', 'awesome test forum')
        thread = self.app.testforum.testthread
        self.app._setObject(forum.id, forum)
        subscriptions.add(thread, '123456')
        self.app.anotherforum._setObject(thread.id, thread)
        thread.forum = forum
        ev = ObjectMovedEvent(thread, self.app.testforum, thread.id, self.app.anotherforum, thread.id)
        subscriptions.move_subscribers(ev)
        expected = 'anotherforum/testthread'
        got = subscriptions.key_for_obj(self.app.anotherforum.testthread)
        self.failUnless(expected == got, 'unexpected object key: {got}'.format(got=got))
        got = subscriptions.subscribers_for(thread)
        self.failUnless(len(got) == 1, 'expected one subscriber')
        email = got[0].getProperty('email')
        self.failUnless(email == 'max.mustermann@haufe-lexware.com', 'wrong memberdata %s' % got[0])

class ConflictResolutionTests(unittest.TestCase):

    _test_db_name = 'hl.plone.boardnotificatiosn.unittests.fs'

    def _make_one(self):
        from hl.plone.boardnotifications.subscribe import Subscriptions
        return Subscriptions()

    def tearDown(self):
        """
        delete test ZODB
        """
        os.unlink(self._test_db_name)

    def setUp(self):
        try:
            self.tearDown()
        except OSError, error:
            if error.errno != 2:
                raise

    def test_conflict_resolution(self):
        db = ZODB.DB(self._test_db_name)
        tm_A = transaction.TransactionManager()
        conn_A = db.open(transaction_manager=tm_A)
        s_A = conn_A.root()['subscriptions'] = self._make_one()
        for k in range(0, 128, 4):
            # fill 2 buckets
            co = ContentMock('testforum/k')
            s_A.add(co, k)
        tm_A.commit()
        tm_B = transaction.TransactionManager()
        conn_B = db.open(transaction_manager=tm_B)
        s_B = conn_B.root()['subscriptions']
        s_A.add(ContentMock('testforum/13'), 13)
        s_B.add(ContentMock('testforum/93'), 93)
        tm_A.commit()
        tm_B.commit()
        tm_A.begin()
        s_A.remove(ContentMock('testforum/13'), 13)
        s_B.remove(ContentMock('testforum/93'), 93)
        tm_A.commit()
        self.assertRaises(ConflictError, tm_B.commit)
        tm_B.abort()
        tm_A.begin()
        s_A.add(ContentMock('testforum/1'), 1)
        s_B.add(ContentMock('testforum/2'), 2)
        tm_A.commit()
        tm_B.commit()
        tm_A.begin()
        tm_B.begin()
        s_A.add(ContentMock('testforum/1'), 1)
        s_B.remove(ContentMock('testforum/1'), 1)
        tm_A.commit()
        tm_B.commit()


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(SubscriptionTests),
        unittest.makeSuite(ConflictResolutionTests),
        ))

if __name__ == '__main__':
    from Products.GenericSetup.testing import run
    run(test_suite())

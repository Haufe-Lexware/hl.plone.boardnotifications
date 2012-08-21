# -*- coding: utf-8 -*-
import unittest
import transaction
from Testing import ZopeTestCase
from zope.component import getGlobalSiteManager, queryUtility
from Products.MailHost.interfaces import IMailHost
from Products.CMFCore.interfaces import IMembershipTool, IMemberDataTool, ISiteRoot
from mocks import MailHostMock, MembershipToolMock, MemberdataToolMock, MemberDataMock, ForumMock, ConversationMock, CommentMock

class NotifierTestLayer(ZopeTestCase.layer.ZopeLite):

    @classmethod
    def setUp(cls):
        gsm = getGlobalSiteManager()
        gsm.registerUtility(MailHostMock(), IMailHost)
        gsm.registerUtility(MembershipToolMock(), IMembershipTool)
        gsm.registerUtility(MemberdataToolMock(), IMemberDataTool)
        

class NotifierTests(unittest.TestCase):

    layer = NotifierTestLayer

    def setUp(self):
        transaction.begin()
        self.app = ZopeTestCase.app()
        gsm = getGlobalSiteManager()
        gsm.registerUtility(self.app, ISiteRoot)
        self.app.email_from_address = 'forum@lexware.de'
        mtool = queryUtility(IMembershipTool)
        self.app._setObject(mtool.id, mtool)
        mdtool = queryUtility(IMemberDataTool)
        self.app._setObject(mdtool.id, mdtool)
        md1 = MemberDataMock(id='123456',
                             email='max.mustermann@haufe-lexware.com',
                             salutation='Herr',
                             lastname='Mustermann',
                             firstname='Max')
        md2 = MemberDataMock(id='654321',
                             email='liese.mueller@haufe-lexware.com',
                             salutation='Frau',
                             lastname='M\xc3\xbcller',
                             firstname='Liese')
        mtool = queryUtility(IMembershipTool)
        mtool.members[md1['id']] = md1
        mtool.members[md2['id']] = md2
        forum = ForumMock('testforum', 'test forum')
        thread = ConversationMock(id='testthread',
                                  title='test thread',
                                  forum=forum,
                                  creator=md1['id'])
        comment = CommentMock(id='testcomment',
                              title='Re: test',
                              conversation=thread,
                              creator=md2['id'])
        thread.comments.append(comment)
        thread._setObject(comment.id, comment)
        forum._setObject(thread.id, thread)
        self.app._setObject(forum.id, forum)

    def tearDown(self):
        transaction.abort()
        ZopeTestCase.close(self.app)

    def _make_one(self):
        from hl.plone.boardnotifications.notify import Notifier
        return Notifier()

    def _register_subscriptions(self):
        from hl.plone.boardnotifications.subscribe import Subscriptions
        from hl.plone.boardnotifications.interfaces import ISubscriptions
        gsm = getGlobalSiteManager()
        gsm.registerUtility(Subscriptions(), ISubscriptions)
        return queryUtility(ISubscriptions)

    def test_thread_moved(self):
        n = self._make_one()
        n.thread_moved_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\nthreadurl:%(threadurl)s\nboardtitle:%(boardtitle)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'}
        # if a user posts more than one comment, he still should get notified only once.
        comment = CommentMock(id='testcomment2',
                              title='Re: test',
                              conversation=self.app.testforum.testthread,
                              creator='123456')
        self.app.testforum.testthread.comments.append(comment)
        self.app.testforum.testthread._setObject(comment.id, comment)
        mh = queryUtility(IMailHost)
        mh.emails = []
        n.thread_moved(self.app.testforum.testthread)
        got = len(mh.emails)
        self.failUnless(got==2, 'notifier should have sent 2 emails, got %s instead' % got)
        for mail in mh.emails:
            got = {}
            got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
            self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
            self.failUnless(got['threadurl']=='http://nohost/testforum/testthread', 'unexpected thread url, got "%s"' % got['threadurl'])
            self.failUnless(got['boardtitle']=='test forum', 'unexpected board title, got "%s"' % got['boardtitle'])
            self.failUnless(got['signature']=='signature', 'unexpected signature')
            if mail[0][0].get('To') == 'max.mustermann@haufe-lexware.com':
                self.failUnless(got['salutation']=='Sehr geehrter Herr Max Mustermann', 'unexcpected salutation, got "%s"' % got['salutation'])
            else:
                self.failUnless(got['salutation']=='Sehr geehrte Frau Liese M=C3=BCller', 'unexcpected salutation, got "%s"' % got['salutation'])
        mh.emails = []
        n.thread_moved_text = None
        n.thread_moved(self.app.testforum.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is None')
        mh.emails = []
        n.thread_moved_text = ''
        n.thread_moved(self.app.testforum.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is empty')

    def test_comment_edited(self):
        n = self._make_one()
        n.comment_edited_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\nsignature:%(mailsignature)s'
        n.signature = u'signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'} 
        n.comment_edited(self.app.testforum.testthread.testthread)
        mh = queryUtility(IMailHost)
        mail = mh.emails[-1]
        got = {}
        got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
        self.failUnless(got['salutation']=='Sehr geehrter Herr Max Mustermann', 'unexcpected salutation, got "%s"' % got['salutation'])
        self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
        self.failUnless(got['commenturl']=='http://nohost/testforum/testthread/testthread', 'unexpected comment url, got "%s"' % got['commenturl'])
        mh.emails = []
        self.app.portal_membership.authenticated = '123456'
        n.comment_edited(self.app.testforum.testthread.testthread)
        got = len(mh.emails)  
        mh.emails = []
        self.failUnless(got==0, 'no mail should be sent to the creator of a comment if he edits it.')
        self.app.portal_membership.authenticated = None
        n.comment_edited_text = None
        n.comment_edited(self.app.testforum.testthread.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is None')
        mh.emails = []
        n.comment_edited_text = ''
        n.comment_edited(self.app.testforum.testthread.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is empty')

    def test_comment_deleted(self):
        n = self._make_one() 
        n.comment_deleted_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'} 
        n.comment_deleted(self.app.testforum.testthread.testcomment)
        mh = queryUtility(IMailHost)
        mail = mh.emails[-1]
        got = {}
        got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
        self.failUnless(got['salutation']=='Sehr geehrte Frau Liese M=C3=BCller', 'unexcpected salutation, got "%s"' % got['salutation'])
        self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
        self.failUnless(got['commenturl']=='http://nohost/testforum/testthread/testcomment', 'unexpected comment url, got "%s"' % got['commenturl'])
        mh.emails = []
        n.comment_deleted_text = None
        n.comment_deleted(self.app.testforum.testthread.testcomment)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is None')
        mh.emails = []
        n.comment_deleted_text = ''
        n.comment_deleted(self.app.testforum.testthread.testcomment)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is empty')

    def test_subscription_comment_edited(self):
        n = self._make_one()
        subscriptions = self._register_subscriptions()
        subscriptions.add(self.app.testforum.testthread, '654321')
        n.subscription_comment_edited_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'} 
        mh = queryUtility(IMailHost)
        mh.emails = []
        n.subscription_comment_edited(self.app.testforum.testthread.testthread)
        self.failUnless(len(mh.emails)==1, 'expected one mail for one subscriber')
        mail = mh.emails[-1]
        got = {}
        got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
        self.failUnless(got['salutation']=='Sehr geehrte Frau Liese M=C3=BCller', 'unexcpected salutation, got "%s"' % got['salutation'])
        self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
        self.failUnless(got['commenturl']=='http://nohost/testforum/testthread/testthread', 'unexpected comment url, got "%s"' % got['commenturl'])
        comment = CommentMock(id='testcomment2',
                              title='Re: test',
                              conversation=self.app.testforum.testthread,
                              creator='123456')
        self.app.testforum.testthread.comments.append(comment)
        self.app.testforum.testthread._setObject(comment.id, comment)
        subscriptions.add(self.app.testforum.testthread, '123456')
        mh.emails = []   
        n.subscription_comment_edited(self.app.testforum.testthread.testcomment2)
        got = len(mh.emails)
        self.failUnless(got==1, 'expected one email, got %s' % got)
        mail = mh.emails[-1]
        got = {}
        got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
        self.failUnless(got['salutation']=='Sehr geehrte Frau Liese M=C3=BCller', 'unexcpected salutation, got "%s"' % got['salutation'])
        mh.emails = []
        n.subscription_comment_edited_text = None
        n.subscription_comment_edited(self.app.testforum.testthread.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is None')
        mh.emails = []
        n.subscription_comment_edited_text = ''
        n.subscription_comment_edited(self.app.testforum.testthread.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is empty')

    def test_subscription_comment_added(self):
        n = self._make_one()
        subscriptions = self._register_subscriptions()
        subscriptions.add(self.app.testforum.testthread, '123456')
        n.subscription_comment_added_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'} 
        mh = queryUtility(IMailHost)
        mh.emails = []
        n.subscription_comment_added(self.app.testforum.testthread.testcomment)
        mail = mh.emails[-1]
        got = {}
        got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
        self.failUnless(got['salutation']=='Sehr geehrter Herr Max Mustermann', 'unexcpected salutation, got "%s"' % got['salutation'])
        self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
        self.failUnless(got['commenturl']=='http://nohost/testforum/testthread/testcomment', 'unexpected comment url, got "%s"' % got['commenturl'])
        # a user will not be notified if he is the author of the comment
        comment = CommentMock(id='testcomment2',
                              title='Re: test',
                              conversation=self.app.testforum.testthread,
                              creator='654321')
        self.app.testforum.testthread.comments.append(comment)
        self.app.testforum.testthread._setObject(comment.id, comment)
        subscriptions.add(self.app.testforum.testthread, '654321')
        mh.emails = [] 
        n.subscription_comment_added(self.app.testforum.testthread.testcomment2)
        got = len(mh.emails)
        self.failUnless(got==1, 'expected one email, got %s' % got)
        mail = mh.emails[-1]
        got = {}
        got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
        self.failUnless(got['salutation']=='Sehr geehrter Herr Max Mustermann', 'unexcpected salutation, got "%s"' % got['salutation'])
        mh.emails = [] 
        n.subscription_comment_added_text = None
        n.subscription_comment_added(self.app.testforum.testthread.testcomment)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is None')
        mh.emails = [] 
        n.subscription_comment_added_text = ''
        n.subscription_comment_added(self.app.testforum.testthread.testcomment)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is empty')

    def test_parse_email_headers(self):
        n = self._make_one()
        n.comment_edited_text = u'Subject:Changes in %(threadurl)s\n\nsalutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\nsignature:%(mailsignature)s'
        n.signature = u'signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'}
        mh = queryUtility(IMailHost)
        mh.emails = []
        n.comment_edited(self.app.testforum.testthread.testthread)
        mail = mh.emails[-1]
        got = {}
        msg = mail[0][0]
        got.update([tuple(kv.split(':', 1)) for kv in msg.as_string().split('\n\n')[1].split('\n')])
        self.failUnless(msg['Subject']=='Changes in http://nohost/testforum/testthread', 'unexpected email subject, got "%s"' % msg['Subject'])
        self.failUnless(got['salutation']=='Sehr geehrter Herr Max Mustermann', 'unexcpected salutation, got "%s"' % got['salutation'])
        self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
        self.failUnless(got['commenturl']=='http://nohost/testforum/testthread/testthread', 'unexpected comment url, got "%s"' % got['commenturl'])
        self.failUnless(got['signature']=='signature', 'unexpected signature, got "%s"' % got['signature'])
        mh.emails = []


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(NotifierTests),
        ))

if __name__ == '__main__':
    from Products.GenericSetup.testing import run
    run(test_suite())


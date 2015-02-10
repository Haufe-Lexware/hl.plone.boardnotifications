# -*- coding: utf-8 -*-
import unittest
import transaction
from Testing import ZopeTestCase
from zope.component import getGlobalSiteManager, queryUtility
from zope.interface.verify import verifyObject
from Products.MailHost.interfaces import IMailHost
from Products.CMFCore.interfaces import IMembershipTool, IMemberDataTool, ISiteRoot
from mocks import MailHostMock, MembershipToolMock, MemberdataToolMock, MemberDataMock, ForumMock, ConversationMock, CommentMock
from hl.plone.boardnotifications.interfaces import INotifier


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
        md3 = MemberDataMock(id='123321',
                             email='nobody@haufe-lexware.com',
                             salutation='Frau',
                             lastname='Body',
                             firstname='No')
        mtool = queryUtility(IMembershipTool)
        mtool.members[md1['id']] = md1
        mtool.members[md2['id']] = md2
        mtool.members[md3['id']] = md3
        forum = ForumMock('testforum', 'test forum')
        thread = ConversationMock(id='testthread',
                                  title='test thread',
                                  forum=forum,
                                  creator=md1['id'],
                                  commenttext=u'Awesome – first comment!')
        comment = CommentMock(id='testcomment',
                              title='Re: test',
                              conversation=thread,
                              text=u'Awesome – second comment!'.encode('utf-8'),
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

    def test_interface(self):
        verifyObject(INotifier, self._make_one())

    def test_thread_moved(self):
        n = self._make_one()
        n.thread_moved_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\nthreadurl:%(threadurl)s\nboardtitle:%(boardtitle)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'}
        # if a user posts more than one comment, he still should get notified only once.
        comment = CommentMock(id='testcomment2',
                              title='Re: test',
                              conversation=self.app.testforum.testthread,
                              text='Awesome third comment!',
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
                self.failUnless(got['salutation']=='Sehr geehrter Herr Max Mustermann', 'unexpected salutation, got "%s"' % got['salutation'])
            else:
                self.failUnless(got['salutation']=='Sehr geehrte Frau Liese M=C3=BCller', 'unexpected salutation, got "%s"' % got['salutation'])
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
        mh.emails = []
        n.thread_moved_text = ' \r\n '
        n.thread_moved(self.app.testforum.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template contains only whitespace')

    def test_thread_moved_missing_memberdata(self):
        n = self._make_one()
        n.thread_moved_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\nthreadurl:%(threadurl)s\nboardtitle:%(boardtitle)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'}
        # if a user posts more than one comment, he still should get notified only once.
        comment = CommentMock(id='testcomment2',
                              title='Re: test',
                              conversation=self.app.testforum.testthread,
                              text='Awesome!',
                              creator='123456')
        self.app.testforum.testthread.comments.append(comment)
        self.app.testforum.testthread._setObject(comment.id, comment)
        mh = queryUtility(IMailHost)
        mh.emails = []
        mtool = queryUtility(IMembershipTool)
        mtool.members['654321'] = None
        n.thread_moved(self.app.testforum.testthread)
        got = len(mh.emails)
        self.failUnless(got==1, 'notifier should have sent 1 email, got %s instead' % got)
        mail = mh.emails[0]
        got = {}
        got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
        self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
        self.failUnless(got['threadurl']=='http://nohost/testforum/testthread', 'unexpected thread url, got "%s"' % got['threadurl'])
        self.failUnless(got['boardtitle']=='test forum', 'unexpected board title, got "%s"' % got['boardtitle'])
        self.failUnless(got['signature']=='signature', 'unexpected signature')
        self.failUnless(got['salutation']=='Sehr geehrter Herr Max Mustermann', 'unexpected salutation, got "%s"' % got['salutation'])

    def test_comment_edited(self):
        n = self._make_one()
        n.comment_edited_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\ncommenttext:%(commenttext)s\nsignature:%(mailsignature)s'
        n.signature = u'signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'} 
        n.comment_edited(self.app.testforum.testthread.testthread)
        mh = queryUtility(IMailHost)
        mail = mh.emails[-1]
        got = {}
        got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
        self.failUnless(got['salutation']=='Sehr geehrter Herr Max Mustermann', 'unexpected salutation, got "%s"' % got['salutation'])
        self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
        self.failUnless(got['commenturl']=='http://nohost/testforum/testthread/testthread', 'unexpected comment url, got "%s"' % got['commenturl'])
        self.failUnless(got['commenttext']=='Awesome =E2=80=93 first comment!', 'unexpected comment text, got "%s"' % got['commenttext'])
        mh.emails = []
        self.app.portal_membership.authenticated = '123456'
        n.comment_edited(self.app.testforum.testthread.testthread)
        got = len(mh.emails)  
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
        mh.emails = []
        n.comment_edited_text = ' \r\n   '
        n.comment_edited(self.app.testforum.testthread.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template contains only whitespace')

    def test_comment_edited_missing_memberdata(self):
        n = self._make_one()
        n.comment_edited_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\ncommenttext:%(commenttext)s\nsignature:%(mailsignature)s'
        n.signature = u'signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'} 
        mtool = queryUtility(IMembershipTool)
        mtool.members['123456'] = None
        mh = queryUtility(IMailHost)
        mh.emails = []
        n.comment_edited(self.app.testforum.testthread.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'comment creator has been deleted - no mail should be sent')

    def test_comment_deleted(self):
        n = self._make_one() 
        n.comment_deleted_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\ncommenttext:%(commenttext)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'} 
        n.comment_deleted(self.app.testforum.testthread.testcomment)
        mh = queryUtility(IMailHost)
        mail = mh.emails[-1]
        got = {}
        got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
        self.failUnless(got['salutation']=='Sehr geehrte Frau Liese M=C3=BCller', 'unexpected salutation, got "%s"' % got['salutation'])
        self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
        self.failUnless(got['commenturl']=='http://nohost/testforum/testthread/testcomment', 'unexpected comment url, got "%s"' % got['commenturl'])
        self.failUnless(got['commenttext']==u'Awesome =E2=80=93 second comment!', 'unexpected comment text, got "%s"' % got['commenttext'])
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
        mh.emails = []
        n.comment_deleted_text = ' \r\n '
        n.comment_deleted(self.app.testforum.testthread.testcomment)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template contains only whitespace')

    def test_comment_deleted_missing_memberdata(self):
        n = self._make_one()
        n.comment_deleted_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\ncommenttext:%(commenttext)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'}
        mtool = queryUtility(IMembershipTool)
        mtool.members['654321'] = None
        mh = queryUtility(IMailHost)
        mh.emails = []
        n.comment_deleted(self.app.testforum.testthread.testcomment)
        got = len(mh.emails)
        self.failUnless(got==0, 'comment creator has been deleted - no mail should be sent')

    def test_subscription_comment_edited(self):
        n = self._make_one()
        subscriptions = self._register_subscriptions()
        # Subscribe to the forum
        subscriptions.add(self.app.testforum, '123321')
        # Subscribe to a thread
        subscriptions.add(self.app.testforum.testthread, '654321')
        n.subscription_comment_edited_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\ncommenttext:%(commenttext)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'} 
        mh = queryUtility(IMailHost)
        mh.emails = []
        n.subscription_comment_edited(self.app.testforum.testthread.testthread)
        self.failUnless(len(mh.emails)==2, 'expected two mails for two subscribers')
        for mail in mh.emails:
            got = {}
            got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
            self.failUnless(got['salutation'] in ['Sehr geehrte Frau Liese M=C3=BCller', 'Sehr geehrte Frau No Body'], 'unexpected salutation, got "%s"' % got['salutation'])
            self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
            self.failUnless(got['commenturl']=='http://nohost/testforum/testthread/testthread', 'unexpected comment url, got "%s"' % got['commenturl'])
            self.failUnless(got['commenttext']==u'Awesome =E2=80=93 first comment!', 'unexpected comment text, got "%s"' % got['commenttext'])
        comment = CommentMock(id='testcomment2',
                              title='Re: test',
                              conversation=self.app.testforum.testthread,
                              text='Awesome!',
                              creator='123456')
        self.app.testforum.testthread.comments.append(comment)
        self.app.testforum.testthread._setObject(comment.id, comment)
        subscriptions.add(self.app.testforum.testthread, '123456')
        mh.emails = []
        n.subscription_comment_edited(self.app.testforum.testthread.testcomment2)
        self.failUnless(len(mh.emails)==2, 'expected two mails for two subscribers')
        for mail in mh.emails:
            mail = mh.emails[-1]
            got = {}
            got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
            self.failUnless(got['salutation'] in ['Sehr geehrte Frau Liese M=C3=BCller', 'Sehr geehrte Frau No Body'], 'unexpected salutation, got "%s"' % got['salutation'])
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
        mh.emails = []
        n.subscription_comment_edited_text = ' \r\n '
        n.subscription_comment_edited(self.app.testforum.testthread.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template contains only whitespace')

    def test_subscription_comment_added(self):
        n = self._make_one()
        subscriptions = self._register_subscriptions()
        # Subscribe to the forum
        subscriptions.add(self.app.testforum, '123321')
        # Subscribe to a thread
        subscriptions.add(self.app.testforum.testthread, '123456')
        n.subscription_comment_added_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\ncommenturl:%(commenturl)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'} 
        mh = queryUtility(IMailHost)
        mh.emails = []
        n.subscription_comment_added(self.app.testforum.testthread.testcomment)
        for mail in mh.emails:
            got = {}
            got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
            self.failUnless(got['salutation'] in ['Sehr geehrter Herr Max Mustermann', 'Sehr geehrte Frau No Body'], 'unexpected salutation, got "%s"' % got['salutation'])
            self.failUnless(got['threadtitle']=='test thread', 'unexpected thread title, got "%s"' % got['threadtitle'])
            self.failUnless(got['commenturl']=='http://nohost/testforum/testthread/testcomment', 'unexpected comment url, got "%s"' % got['commenturl'])
        # a user will not be notified if he is the author of the comment
        comment = CommentMock(id='testcomment2',
                              title='Re: test',
                              conversation=self.app.testforum.testthread,
                              text='Awesome!',
                              creator='654321')
        self.app.testforum.testthread.comments.append(comment)
        self.app.testforum.testthread._setObject(comment.id, comment)
        subscriptions.add(self.app.testforum.testthread, '654321')
        mh.emails = [] 
        n.subscription_comment_added(self.app.testforum.testthread.testcomment2)
        got = len(mh.emails)
        self.failUnless(got==2, 'expected two emails, got %s' % got)
        for mail in mh.emails:
            got = {}
            got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
            self.failUnless(got['salutation'] in ['Sehr geehrter Herr Max Mustermann', 'Sehr geehrte Frau No Body'], 'unexpected salutation, got "%s"' % got['salutation'])
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
        mh.emails = [] 
        n.subscription_comment_added_text = ' \r\n\t '
        n.subscription_comment_added(self.app.testforum.testthread.testcomment)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template contains only whitespace')

    def test_subscription_thread_moved(self):
        n = self._make_one()
        subscriptions = self._register_subscriptions()
        # Subscribe to the forum
        subscriptions.add(self.app.testforum, '123321')
        # Subscribe to a thread
        subscriptions.add(self.app.testforum.testthread, '123456')
        n.subscription_thread_moved_text = u'salutation:%(salutation)s\nthreadtitle:%(threadtitle)s\nthreadurl:%(threadurl)s\nboardtitle:%(boardtitle)s\nsignature:%(mailsignature)s'
        n.signature='signature'
        n.salutations = {u'Herr':u'Sehr geehrter Herr %(firstname)s %(lastname)s', u'Frau':u'Sehr geehrte Frau %(firstname)s %(lastname)s'}
        mh = queryUtility(IMailHost)
        mh.emails = []
        n.subscription_thread_moved(self.app.testforum.testthread)
        got = len(mh.emails)
        self.failUnless(got==2, 'notifier should have sent 2 emails, got %s instead' % got)
        for mail in mh.emails:
            got = {}   
            got.update([tuple(kv.split(':', 1)) for kv in mail[0][0].as_string().split('\n\n')[1].split('\n')])
            self.failUnless(got['salutation'] in ['Sehr geehrter Herr Max Mustermann', 'Sehr geehrte Frau No Body'], 'unexpected salutation, got "%s"' % got['salutation'])
        mh.emails = []
        n.subscription_thread_moved_text = None
        n.subscription_thread_moved(self.app.testforum.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is None')
        mh.emails = []
        n.subscription_thread_moved_text = ''
        n.subscription_thread_moved(self.app.testforum.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template is empty')
        mh.emails = []
        n.subscription_thread_moved_text = ' \r\n '
        n.subscription_thread_moved(self.app.testforum.testthread)
        got = len(mh.emails)
        self.failUnless(got==0, 'no mails should be sent if the mail template contains only whitespace')

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
        self.failUnless(got['salutation']=='Sehr geehrter Herr Max Mustermann', 'unexpected salutation, got "%s"' % got['salutation'])
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


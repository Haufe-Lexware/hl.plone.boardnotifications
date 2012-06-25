from zope.interface import Interface
from zope.schema import Text, TextLine
from zope.i18nmessageid import MessageFactory
_ = MessageFactory('hl.plone.boardnotifications')


class INotifier(Interface):

    """
    notify in case of changes to comments/threads
    """


class ISubscriptions(Interface):

    """
    manage notification subscriptions for threads
    """


class INotifierSchema(Interface):

    """
    schema for the notifiers configuration
    """

    subject = TextLine(title=_(u'Subject'),
                       description=_(u'Mail subject'))

    signature = Text(title=_(u'Signature'),
                     description=_(u'Mail signature'))

    salutations = Text(title=_(u'Map Salutations'),
                       required=False,
                       description=_(u'Map salutation from memberdata property to email salutation (one mapping per line, use : to separate key and value).'))

    comment_edited_text = Text(title=_(u'Comment edited'),
                               required=False,
                               description=_(u'Mail text when a comment has been edited'))

    thread_moved_text = Text(title=_(u'Thread moved'),
                             required=False,
                             description=_(u'Mail text when a thread has been moved to another board'))

    comment_deleted_text = Text(title=_(u'Comment deleted'),
                                required=False,
                                description=_(u'Mail text when a comment has been deleted'))

    subscription_comment_edited_text = Text(title=_(u'Comment edited (Subscriber)'),
                                required=False,
                                description=_(u'Mail text to send to subscribers of a thread where a comment has been edited'))

    subscription_comment_added_text = Text(title=_(u'Comment added (Subscriber)'),
                                required=False,
                                description=_(u'Mail text to send to subscribers of a thread where a comment has been added'))


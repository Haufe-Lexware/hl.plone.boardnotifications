from zope.component import adapter, queryUtility
from zope.lifecycleevent.interfaces import IObjectMovedEvent, IObjectModifiedEvent, IObjectRemovedEvent, IObjectAddedEvent
from Products.Archetypes.interfaces import IObjectEditedEvent
from Products.Ploneboard.interfaces import IConversation, IComment
from .notify import INotifier


@adapter(IConversation, IObjectMovedEvent)
def threadmoved(conv, event):
    """
    send email notification when a thread was moved
    """
    if IObjectRemovedEvent.providedBy(event) or IObjectAddedEvent.providedBy(event):
        return
    n = queryUtility(INotifier)
    n.thread_moved(conv)

@adapter(IComment, IObjectModifiedEvent)
def commentedited(comment, event):
    """
    send email notification when a comment has been edited
    """
    n = queryUtility(INotifier)
    n.comment_edited(comment)

@adapter(IComment, IObjectEditedEvent)
def subscriptioncommentedited(comment, event):
    """
    send email notification to thread subscribers when a comment has been edited
    """
    n = queryUtility(INotifier)
    n.subscription_comment_edited(comment)

@adapter(IComment, IObjectAddedEvent)
def subscriptioncommentadded(comment, event):
    """
    send email notification to thread subscribers when a comment has been added
    """
    n = queryUtility(INotifier)
    # XXX imho the following call is missing in PloneboardComment.addReply, s. http://plone.org/products/ploneboard/issues/240
    comment.unmarkCreationFlag()
    n.subscription_comment_added(comment)

@adapter(IComment, IObjectRemovedEvent)
def commentdeleted(comment, event):
    """
    send email notification when a comment has been edited
    """
    n = queryUtility(INotifier)
    n.comment_deleted(comment)
    

from zope.component import adapter, queryUtility
from zope.lifecycleevent.interfaces import (
        IObjectAddedEvent,
        IObjectModifiedEvent,
        IObjectMovedEvent,
        IObjectRemovedEvent,
        )
from Products.Archetypes.interfaces import (
        IObjectEditedEvent,
        IObjectInitializedEvent,
        )
from Products.Ploneboard.interfaces import IConversation, IComment
from .interfaces import INotifier, ISubscriptions


@adapter(IConversation, IObjectMovedEvent)
def threadmoved(conv, event):
    """
    Send email notification when a thread was moved
    """
    if IObjectRemovedEvent.providedBy(event) or IObjectAddedEvent.providedBy(event):
        return
    n = queryUtility(INotifier)
    n.thread_moved(conv)
    s = queryUtility(ISubscriptions)
    s.move_subscribers(event)

@adapter(IComment, IObjectModifiedEvent)
def commentedited(comment, event):
    """
    Send email notification when a comment has been edited
    """
    n = queryUtility(INotifier)
    n.comment_edited(comment)

@adapter(IComment, IObjectEditedEvent)
def subscriptioncommentedited(comment, event):
    """
    Send email notification to thread subscribers when a comment has been edited
    """
    n = queryUtility(INotifier)
    n.subscription_comment_edited(comment)

@adapter(IComment, IObjectInitializedEvent)
def subscriptioncommentadded(comment, event):
    """
    Send email notification to thread subscribers when a comment has been added
    """
    n = queryUtility(INotifier)
    # XXX imho the following call is missing in PloneboardComment.addReply, s. http://plone.org/products/ploneboard/issues/240
    comment.unmarkCreationFlag()
    n.subscription_comment_added(comment)

@adapter(IComment, IObjectRemovedEvent)
def commentdeleted(comment, event):
    """
    Send email notification when a comment has been deleted
    """
    n = queryUtility(INotifier)
    if n is None:
        return
    n.comment_deleted(comment)


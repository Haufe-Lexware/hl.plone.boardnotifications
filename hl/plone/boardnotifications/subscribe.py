import logging
from BTrees.OOBTree import OOBTree
from persistent.list import PersistentList
from zope.interface import implements
from Products.CMFCore.utils import getToolByName
from .interfaces import ISubscriptions

log = logging.getLogger('hl.plone.boardnotifications.subscribe')


class Subscriptions(OOBTree):

    """
    Part of this code has been taken from Products.PloneboardSubscription
    """

    implements(ISubscriptions)

    @staticmethod
    def key_for_obj(obj):
        return '/'.join(obj.getPhysicalPath()) 

    def subscribers_for(self, obj):
        key = self.key_for_obj(obj)
        subscriberids = self.get(key)
        if subscriberids is None:
            return []
        mtool = getToolByName(obj, 'portal_membership')
        return filter(lambda o: o is not None, [mtool.getMemberById(sid) for sid in subscriberids])

    def add(self, obj, user):
        """
        Adds user
        """
        obj_id = self.key_for_obj(obj)
        if obj_id not in self.keys():
            self[obj_id] = PersistentList()
        if user not in self[obj_id]:
            log.info('Subscribing user %s to %s' % (user,  obj_id))
            self[obj_id].append(user)

    def check_subscriber(self, obj):
        """
        Checks user
        """
        mtool = getToolByName(obj, 'portal_membership')
        user = mtool.getAuthenticatedMember().getId()
        return self.check_subscriber_id(self.key_for_obj(obj), user)

    def check_subscriber_id(self, obj_id, user):
        """
        Checks user
        """
        if obj_id not in self.keys():
            return False
        return user in self[obj_id]

    def remove(self, obj, user):
        """
        Deletes user
        """
        obj_id = self.key_for_obj(obj)
        if self.check_subscriber_id(obj_id, user):
            log.info('Removing subscription of user %s to %s' % (user, obj_id))
            self[obj_id].remove(user)
            if len(self[obj_id]) == 0:
                del self[obj_id]

    def move_subscribers(self, object_moved_event):
        """
        a thread is being moved from one forum to another - 
        move subscriptions also.
        """
        old_key = '{forum}/{thread}'.format(forum='/'.join(object_moved_event.oldParent.getPhysicalPath()), thread=object_moved_event.oldName)
        new_key = self.key_for_obj(object_moved_event.object)
        self[new_key] = self[old_key]
        del self[old_key]

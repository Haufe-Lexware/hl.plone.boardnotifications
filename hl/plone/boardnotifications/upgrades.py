from BTrees.OOBTree import OOBTree
from zope.component import getUtility
from .interfaces import ISubscriptions


def upgrade_subscriptions(self):
    """ make sure subscriptions are stored in an OOBTree
    """
    existing = getUtility(ISubscriptions)
    data = OOBTree()
    for k, v in existing.data.items():
        data[k] = v
    del existing.data
    existing.data = data



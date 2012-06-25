from UserDict import UserDict
from AccessControl.SpecialUsers import nobody
from OFS.SimpleItem import SimpleItem
from OFS.Folder import Folder


class MailHostMock(object):

    def __init__(self):
        self.emails = []

    def send(self, *args, **kwargs):
        self.emails.append((args, kwargs))


class MembershipToolMock(SimpleItem):
    """
    mock portal_membership as needed
    """
    id = 'portal_membership'

    def __init__(self):
        self.members = {}
        self.authenticated = None

    def getMemberById(self, memberid):
        return self.members.get(memberid)

    def getAuthenticatedMember(self):
        return self.members.get(self.authenticated, nobody)


class MemberdataToolMock(SimpleItem):
    """
    ... portal_memberdata ...
    """
    id = 'portal_memberdata'

    def __init__(self, property_ids=('email', 'firstname', 'lastname', 'salutation')):
        self.property_ids = property_ids

    def propertyIds(self):
        return self.property_ids


class MemberDataMock(UserDict):

    getProperty = UserDict.__getitem__

    def getId(self):
        return self['id']


class ContentMock(SimpleItem):
    """
    Dublin Core as needed
    """

    def __init__(self, id, title, creator=None):
        self.id = id
        self.title = title
        self.creator = creator

    def Creator(self):
        return self.creator

    def Title(self):
        return self.title

    def absolute_url(self):
        return 'http://nohost/%s' % self.id


class ForumMock(ContentMock, Folder):
    
    def __init__(self, id, title):
        ContentMock.__init__(self, id, title)
        Folder.__init__(self, id)

    def getPhysicalPath(self):
        return (self.id,)


class ConversationMock(ContentMock, Folder):
    """
    mock relevant interface of PloneboardConversation
    """

    def __init__(self, id, title, forum, creator=None):
        Folder.__init__(self, id)
        ContentMock.__init__(self, id, title, creator)
        self.forum = forum
        self.comments = []
        comment = CommentMock(id, title, self, creator)
        self.comments.append(comment)
        self._setObject(id, comment)
        comment = comment.__of__(self)

    def getForum(self):
        return self.forum

    def absolute_url(self):
        return '%s/%s' % (self.forum.absolute_url(), self.id)

    def getComments(self):
        return [self[comment.id] for comment in self.comments]

    def getPhysicalPath(self):
        return self.getForum().getPhysicalPath() + (self.id,)


class CommentMock(ContentMock):
    """
    mock relevant interface of PloneboardComment
    """

    def __init__(self, id, title, conversation, creator=None):
        super(CommentMock, self).__init__(id, title, creator)
        self.conversation = conversation

    def getConversation(self):
        return self.conversation

    def absolute_url(self):
        return '%s/%s' % (self.conversation.absolute_url(), self.id)


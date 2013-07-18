import re
import base64
import logging
import urlparse
from email.Errors import HeaderParseError
from email import message_from_string
try:
    from email import utils as email_utils
    email_utils  # pyflakes
except ImportError:
    # BBB Python 2.4
    from email import Utils as email_utils
from email import Header

from zExceptions import NotFound
from AccessControl import Unauthorized
from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.SecurityManagement import setSecurityManager
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import UnrestrictedUser
from OFS.Image import File
from zope.component import getUtility
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView

from hl.plone.boardnotifications.interfaces import INotifier

logger = logging.getLogger('hl.plone.boardnotifications.mailin')
URL_RE = re.compile(r'\b(([\w-]+://?|www[.])[^\s()<>]+(?:\([\w\d]+\)|([^[:punct:]\s]|/)))')

# Ripped bodily from poimail.py, thank you Maurits!


class Receiver(BrowserView):

    def __init__(self, context, request):
        super(Receiver, self).__init__(context, request)
        notifier = getUtility(INotifier)
        self.enabled = notifier.mailin_enabled
        self.listen_addresses = notifier.listen_addresses
        self.fake_manager = notifier.fake_manager
        self.add_attachments = notifier.add_attachments

    def __call__(self):
        if not self.enabled:
            logger.debug('received mail-in request, but mail-in not enabled')
            raise NotFound
        mail = self.request.get('Mail', '')
        mail = mail.strip()
        if not mail:
            msg = u'No mail found in request'
            logger.warn(msg)
            return msg
        message = message_from_string(mail)

        logger.debug('--------')
        logger.debug(mail)
        logger.debug('--------')
        logger.debug(message)
        from_addresses = self.get_addresses(message, 'From')
        to_addresses = self.get_addresses(message, 'To')
        if not from_addresses or not to_addresses:
            msg = u'No From or To address found in request'
            logger.warn(msg)
            return msg
        for from_name, from_address in from_addresses:
            if from_address:
                break
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        email_from_address = portal.getProperty('email_from_address')
        if from_address.lower() == email_from_address.lower():
            # This too easily means that a message sent by Poi ends up
            # being added as a reply on an issue that we have just
            # created.
            msg = u'Ignoring mail from portal email_from_address'
            logger.info(msg)
            return msg

        subject_line = message.get('Subject', '')
        subjects = []
        decoded = Header.decode_header(subject_line)
        for decoded_string, charset in decoded:
            if charset:
                decoded_string = decoded_string.decode(charset)
            subjects.append(decoded_string)
        subject = u' '.join(subjects)

        logger.debug("Forum at %s received mail from %r to %r with "
                     "subject %r", self.context.absolute_url(),
                     from_address, to_addresses, subject)
        text, mimetype = self.get_text_and_mimetype(message)
        if not text:
            text = "Warning: no text found in email"
            mimetype = 'text/plain'
            logger.warn(text)
        logger.debug('Got payload with mimetype %s from email.', mimetype)

        # Create an attachment from the complete email.
        attachment = File('email.eml', 'E-mail', mail)

        tags = self.get_tags(message)
        if tags:
            logger.debug("Determined tags: %r", tags)
        else:
            logger.debug("Could not determine tags.")

        # Store original security manager.
        sm = getSecurityManager()
        # Possibly switch to a different user.
        self.switch_user(from_address)

        if self.add_attachments:
            attachments = self.get_attachments(message)
            attachments = [File(filename, filename, data) for filename, data in attachments]
        else:
            attachments = [attachment]

        target = self.find_conversation_or_thread(subject, text, tags, message)
        if target is None:
            # We don't allow creating conversations from mail, only replies
            logger.info('Could not find something to reply to')
        else:
            try:
                self.add_response(target, from_address, subject, text, mimetype, attachments)
            except Unauthorized, exc:
                logger.error(u'Unauthorized to add response: %s', exc)
                return u'Unauthorized'
            logger.info('Added mail as response to target %s',
                        target.absolute_url())

        # Restore original security manager
        setSecurityManager(sm)
        return mail

    def switch_user(self, from_address):
        """Switch the user.

        This possibly does two things:

        1. Switch to the user that belongs to the given email address.

        2. Give the user the Manage role for the duration of this
           request.

        This view is normally used by the smtp2zope script (or
        something similar) on the local machine.  That script may
        submit anonymously.  That could mean the current user does not
        have enough permissions to submit an issue or add a response.
        So we elevate his privileges by giving him the Manager role.
        But when we do that, this means anonymous users could abuse
        this to submit through the web.  That is not good.  So we only
        elevate privileges when the request originates on the local
        computer.
        """
        sm = getSecurityManager()
        remote_address = self.request.get('HTTP_X_FORWARDED_FOR')
        if not remote_address:
            # Note that request.get('HTTP_something') always returns
            # at least an empty string, also when the key is not in
            # the request, so a default value would be ignored.
            remote_address = self.request.get('REMOTE_ADDR')
        if remote_address not in self.listen_addresses:
            return

        # First, see if we can get an existing user based on the From
        # address.
        pas = getToolByName(self.context, 'acl_users')
        users = pas.searchUsers(email=from_address)
        # Also try lowercase
        from_address = from_address.lower()
        if not users:
            users = pas.searchUsers(email=from_address)
        # If 'email' is not in the properties (say: ldap), we can get
        # far too many results; so we do a double check.  Also,
        # apparently ldap can leave '\r\n' at the end of the email
        # address, so we strip it.  And we compare lowercase.
        users = [user for user in users if user.get('email') and
                 user.get('email').strip().lower() == from_address]
        user = None
        switched = False
        if users:
            user_id = users[0]['userid']
            user = pas.getUserById(user_id)
            if user:
                switched = True
        if not user:
            user = sm.getUser()
            # Getting the user id can be tricky.
            if hasattr(user, 'name'):
                # Works for Anonymous Users
                user_id = user.name
            elif hasattr(user, 'getUserId'):
                # Plone users
                user_id = user.getUserId()
            elif hasattr(user, 'getId'):
                # Root zope users
                user_id = user.getId()
            else:
                # Right...
                return

        # See if this user already has the Manager role, otherwise add it.
        if self.fake_manager and not user.allowed(self.context, ('Manager', )):
            logger.debug("Faking Manager role for user %s", user_id)
            user = UnrestrictedUser(user_id, '', ['Manager'], '')
            faked = True
        else:
            faked = False
        # Now see if we changed something.
        if not (faked or switched):
            return
        newSecurityManager(self.request, user)
        if switched:
            logger.debug("Switched to user %s", user_id)
        if faked:
            logger.debug("Faking Manager role for user %s", user_id)

    def get_addresses(self, message, header_name):
        """Get addresses from the header_name.

        This is usually 'From' or 'To', but other headers may contain
        addresses too, so we allow all, unlike we used to do.

        We expect just one From address and one To address, but
        multiple addresses can also be checked.

        May easily be something ugly like this:
        =?utf-8?q?Portal_Administrator_?=<m.van.rees@zestsoftware.nl>

        From the Python docs:

        decode_header(header)

          Decode a message header value without converting charset.

          Returns a list of (decoded_string, charset) pairs containing
          each of the decoded parts of the header.  Charset is None
          for non-encoded parts of the header, otherwise a lower-case
          string containing the name of the character set specified in
          the encoded string.

          An email.Errors.HeaderParseError may be raised when certain
          decoding error occurs (e.g. a base64 decoding exception).
        """
        if not header_name:
            raise ValueError

        address = message.get(header_name, '')
        try:
            decoded = Header.decode_header(address)
        except HeaderParseError:
            logger.warn("Could not parse header %r", address)
            return []
        logger.debug('Decoded header: %r', decoded)
        for decoded_string, charset in decoded:
            if charset is not None:
                # Surely this is no email address but a name.
                continue
            if '@' not in decoded_string:
                continue

            return email_utils.getaddresses((decoded_string, ))
        return []

    def get_manager(self, message, tags):
        """Determine the responsible manager.

        A custom implementation could pick a manager based on the tags
        that have already been determined.
        """
        default = '(UNASSIGNED)'
        return default

    def get_tags(self, message):
        """Determine the tags that should be set for this post.

        You could add tags based on e.g. the To or From address.
        """
        # TODO: do forum posts have tags?
        return []

    def add_response(self, target, from_address, subject, text, mimetype, attachments):
        # TODO: add all the attachments at once
        # target.addComment(subject, text, creator=None, files=[attachment])
        # TODO: fix quick and dirty text formatting
        text = "<pre>%s</pre>" % text
        if target.meta_type == 'PloneboardConversation':
            target.addComment('answer via mail'+subject, text, creator=from_address, files=attachments)
        elif target.meta_type == 'PloneboardComment':
            target.addReply('answer via mail'+subject, text, creator=from_address, files=attachments)

    def find_conversation_or_thread(self, subject, text, tags, message):
        """Find a conversation or thread for which this email is a response.

        Match based on an URL in the mail.

        The message is passed in as argument as well, to make
        alternative schemes possible.
        """
        target = None
        for match in URL_RE.finditer(text):
            url = match.group(0)
            path = urlparse.urlparse(url).path
            try:
                obj = self.context.unrestrictedTraverse(path[1:])
            except AttributeError:
                # Skip bad URLs
                continue
            if obj.meta_type in ['PloneboardComment',
                    'PloneboardConversation']:
                if target is None:
                    target = obj
                elif (obj.meta_type == 'PloneboardComment' and
                        target.meta_type == 'PloneboardConversation'):
                    # More specific wins
                    target = obj
        return target

    def get_text_and_mimetype(self, message):
        """Get text and mimetype for the body of the response.

        The mimetype is not always needed, but it is good to know
        whether we have html or plain text.

        We prefer to get plain text.  Actually, getting the html from
        the email looks quite okay as long as we put it through the
        safe html transform.
        """
        payload = message.get_payload()
        if not message.is_multipart():
            mimetype = message.get_content_type()
            charset = message.get_content_charset()
            logger.info("Charset: %r", charset)
            if charset and charset != 'utf-8':
                # We only want to store unicode or ascii or utf-8 in
                # Plone.
                # Decode to unicode:
                payload = payload.decode(charset, 'replace')
                # Encode to utf-8:
                payload = payload.encode('utf-8', 'replace')
            return payload, mimetype
        for part in payload:
            if part.is_multipart():
                text, mimetype = self.get_text_and_mimetype(part)
            else:
                text, mimetype = self.part_to_text_and_mimetype(part)
            text = text.strip()
            # Might be empty?
            if text:
                return text, mimetype
        return '', 'text/plain'

    def part_to_text_and_mimetype(self, part):
        if part.get_content_type() == 'text/plain':
            return part.get_payload(decode=True), 'text/plain'
        tt = getToolByName(self.context, 'portal_transforms')
        if part.get_content_type() == 'text/html':
            mimetype = 'text/x-html-safe'
            safe = tt.convertTo(mimetype, part.get_payload(decode=True),
                                mimetype='text/html')
            # Poi responses fail on view when you have the x-html-safe
            # mime type.  Fixed in Poi 1.2.12 (unreleased) but hey, we
            # only need that safe mimetype for the conversion.
            mimetype = 'text/html'
        else:
            # This might not work in all cases, e.g. for attachments,
            # but that is not tested yet.
            mimetype = 'text/plain'
            safe = tt.convertTo(mimetype, part.get_payload(decode=True))
        if safe is None:
            logger.warn("Converting part to mimetype %s failed.", mimetype)
            return u'', 'text/plain'
        return safe.getData(), mimetype

    def get_attachments(self, message):
        """Get attachments.
        """
        payload = message.get_payload()
        if not message.is_multipart():
            mimetype = message.get_content_type()
            if mimetype.startswith('text'):
                return []
            filename = message.get_filename()
            if not filename:
                return []
            encoding = message.get('Content-Transfer-Encoding', '')
            if encoding == 'base64':
                data = base64.decodestring(payload)
            elif encoding == 'binary':
                # Untested.
                data = payload
            else:
                # TODO: support other encodings?  Not sure if this
                # makes sense for anything else.
                return []
            return [(filename, data)]
        attachments = []
        for part in payload:
            attachments.extend(self.get_attachments(part))
        return attachments

    def create_post(self, **kwargs):
        """ Create a post in the given board, and perform workflow and
        rename-after-creation initialisation.
        """
        # We only allow replies to notification, at least for now.
        pass


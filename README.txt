Introduction
============

hl.plone.boardnotifications is yet another package that provides email notifications for Ploneboard (http://pypi.python.org/pypi/Products.Ploneboard) for several purposes. It allows you to:

- Subscribe/Unsubscribe to forum threads
- Notify thread/comment owners when their content has been edited or deleted, moved to a different forum
- configure a specific mail text for each purpose. Leave the mail text empty for notification types you don't want to use
- personalize mails using memberdata properties
- use thread/comment URL and title in the notifications

Installation
============

1. Add the package to your buildout
2. Run buildout
3. Restart Zope
4. Install hl.plone.boardnotifications using the Plone Management Interface
5. Visit "Board Notifications" in the site control panel (go to @@boardnotifier-settings) and configure the mail templates (see "Configuration" below)

Configuration
=============

The following variables are available in the email templates:

- All member properties as defined in portal_memberdata
- Thread title (threadtitle), thread URL (threadurl), forum title (boardtitle) and the comment URL (commenturl) if appropriate
- The salutation field can be used to define gender specific salutations. If you don't need this feature, just leave it blank. When you save your settings, your empty string will be replaces by ':' - simply ignore this. You can still put a generic salutation in each mail template and use %(fullname)s to address the recipient.
- If you want gender specific salutations, hl.plone.boardnotifications defines a new member property named 'salutation'. It is your responsibility to fill it per member by e.g. customizing @@personal-settings. Then you have to map the possible contents of the salutation member property to the desired salutation, e.g.:

    Mr:Dear Mr. %(fullname)s,
    Mrs:Dear Mrs. %(fullname)s,
    :Dear Mrs./Mr. %(fullname)s,

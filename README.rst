Introduction
============


.. image:: https://secure.travis-ci.org/Haufe-Lexware/hl.plone.boardnotifications.png
    :target: http://travis-ci.org/Haufe-Lexware/hl.plone.boardnotifications

.. contents::

``hl.plone.boardnotifications`` provides email notifications for 
`Ploneboard <http://pypi.python.org/pypi/Products.Ploneboard>`__ for several
purposes. It allows you to:

- let users subscribe/unsubscribe to forum threads;
- notify conversation/comment owners when their content has been edited,
  deleted, or moved to a different forum by a moderator;
- configure a specific mail text for each purpose. Leave the mail text empty
  for notification types you don't want to use;
- personalize mails using memberdata properties;
- use conversation/comment URL and title in the notifications.

Installation
============

1. Add the package to your buildout.
2. Run buildout.
3. Restart Zope.
4. Install ``hl.plone.boardnotifications`` using the Plone Control Panel.
5. Visit "Board Notifications" in the site control panel (go to
   ``@@boardnotifier-settings``) and configure the mail templates (see
   `Configuration of Mail Templates`_ below).

Configuration of Mail Templates
===============================

Subject and Signature
---------------------

If you choose to configure subject and signature, those will be used in all
templates. If you want to use subjects and signature on a per-template basis,
leave these fields blank. You can then add the signature to each template as
appropriate. For a per-template subject, enter::

    Subject:your subject here

on the first line of the mail template, followed by a blank line.

Variables
---------

You can use a number of variables to produce meaningful mail texts using
standard Python string interpolation specifiers with the variable name as
mapping key (i.e. ``%(variable_name)s``). The following variables are available
in the email templates:

- all member properties as defined in ``portal_memberdata``;
- conversation title: use ``%(threadtitle)s`` to reference the conversation's
  title;
- conversation URL: use ``%(threadurl)s`` to reference the conversation's URL;
- forum title: use ``%(boardtitle)s`` to reference the forum's title;
- comment URL: use ``%(commenturl)s`` to reference the comment's URL.
- comment text: use ``%(commenttext)s`` to reference the comment's text.

Personalized Mail Salutations
-----------------------------

The salutation field can be used to define gender specific salutations. If you
don't need this feature, just leave it blank. When you save your settings, your
empty string will be replaced by ``:`` - simply ignore this. You can still put a
generic salutation in each mail template and use ``%(fullname)s`` to address
the recipient.

If you want personalized salutations, ``hl.plone.boardnotifications`` defines a
new member property named '``salutation``'. It is your responsibility to fill
it per member by e.g. customizing ``@@personal-settings``. Then you have to map
the possible contents of the salutation member property to the desired
salutation, e.g.::

    Mr:Dear Mr. %(fullname)s,

    Mrs:Dear Mrs. %(fullname)s,

    :Dear Mrs./Mr. %(fullname)s,


Examples of mailing texts
-------------------------

A comment has been added to a conversation, notify conversation subscribers::

    Subject:New comment in thread "%(threadtitle)s"

    %(salutation)s

    There is a new post in thread "%(threadtitle)s", in the forum "%(boardtitle)s".
    You are suscribed to this thread.

    Here is the comment text:
    %(commenttext)s

    Go to the latests post:
    %(commenturl)s

    %(mailsignature)s

    If you don't want to be notified: %(threadurl)s/unsubscribe

    This e-mail has been sent automatically.


A conversation has been moved to another forum::

    Subject:Conversation "%(threadtitle)s" has been moved

    %(salutation)s

    The conversation "%(threadtitle)s" has been moved to "%(boardtitle)s".

    Go to the moved conversation: 
    %(threadurl)s

    %(mailsignature)s


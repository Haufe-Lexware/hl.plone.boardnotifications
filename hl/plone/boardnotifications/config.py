# Where to send the mail.
URL = 'http://user:pass@localhost:8080/Plone/forum'

# We only listen on these addresses.  Or actually, we only do a few
# special tricks to switch the user and give him more priviliges when
# the request comes from one of these addresses.  Make this an empty
# list or tuple if you do not want those special tricks at all.
LISTEN_ADDRESSES = ('127.0.0.1', )

# Should we fake a Manager role to be sure that a post succeeds?
FAKE_MANAGER = True

# Add attachments from the e-mail?  We look for binary attachments.
# These are added as separate responses, as you can only add one
# attachment per issue or response.
ADD_ATTACHMENTS = True

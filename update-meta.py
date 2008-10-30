#!/usr/bin/env python
import logging

from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.contrib.auth.models import User

import search.constants as constants
from search import epubindexer
from library.models import *

log = logging.getLogger('update-meta')
log.setLevel(logging.DEBUG)

# Update all of the metadata in all of the objects on the
# site

for e in EpubArchive.objects.all():
    if e.indexed:
        continue

    log.info("Updating %s (%s)" % (e.title, e.name))
    if e.opf is None or e.opf == '':
        log.warn("Deleting " + e.name)
        e.delete()
        continue
    e.get_subjects()
    e.get_rights()
    e.get_language()
    e.get_publisher()
    e.get_identifier()

    # Get the user for this epub
    user = e.owner

    # Index it
    epubindexer.index_epub(user.username, e)

    # Also index it for the admin users
    admin = User.objects.get(username='liza')
    epubindexer.index_epub(admin.username, e)    

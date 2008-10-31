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
admin = User.objects.get(username='liza')

langs = [l[0] for l in settings.LANGUAGES]

log.info("Will index documents in languages: %s" % langs)

for e in EpubArchive.objects.all().order_by('id'):
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

    # Index it if it's in a language we can handle
    lang = e.get_major_language()
    if lang in langs:
        log.debug("Indexing with lang=%s" % lang)
        epubindexer.index_epub([user.username, admin.username], e)
    else:
        log.warn("skipping %s with lang=%s" % (e.title, lang)


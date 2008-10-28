from django.core.management import setup_environ
import settings
import search.constants as constants
setup_environ(settings)

from library.models import *

# Update all of the metadata in all of the objects on the
# site

for e in EpubArchive.objects.all():
    print "Updating %s (%s)" % (e.title, e.name)
    if e.opf is None or e.opf == '':
        print "Deleting " + e.name
        e.delete()
        continue
    e.get_subjects()
    e.get_rights()
    e.get_language()
    e.get_publisher()
    e.get_identifier()

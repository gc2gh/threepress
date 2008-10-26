from lxml import etree
import os, sys, logging, subprocess, os.path, shutil
import xapian
from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)

import bookworm.search.constants as constants
import bookworm.search.index as index
import bookworm.library.models as models

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('epubindexer')


import os.path, shutil

from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)

def setup():
    pass

def teardown():
    pass

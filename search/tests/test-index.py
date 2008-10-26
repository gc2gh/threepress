from nose.tools import with_setup, assert_not_equals, assert_true, assert_equals, assert_true
import shutil, os.path
from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)
from bookworm.search import index
 
bookworm.settings.SEARCH_ROOT = os.path.join(bookworm.settings.ROOT_PATH, 'search', 'tests', 'dbs')

username = 'testuser'

def setup():
    pass

def teardown():
    shutil.rmtree(bookworm.settings.SEARCH_ROOT)

def test_create_user_database():
    index.create_user_database(username)
    assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username)))


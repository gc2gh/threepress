from nose.tools import with_setup, assert_not_equals, assert_true, assert_equals, assert_false
import shutil, os.path
from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)
from bookworm.search import index
 
bookworm.settings.SEARCH_ROOT = os.path.join(bookworm.settings.ROOT_PATH, 'search', 'tests', 'dbs')

username = 'testuser'
epub_name = 'epub'

def setup():
    pass

def teardown():
    shutil.rmtree(bookworm.settings.SEARCH_ROOT)

def test_create_user_database():
    index.create_user_database(username)
    assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username)))

def test_delete_user_database():
    index.create_user_database(username)
    assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username)))
    index.delete_user_database(username)
    assert_false(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username)))

def test_create_epub_database():
    index.create_epub_database(username, epub_name)
    assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username, epub_name)))

def test_delete_epub_database():
    index.create_epub_database(username, epub_name)
    assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username, epub_name)))
    index.delete_epub_database(username, epub_name)
    assert_false(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username, epub_name)))


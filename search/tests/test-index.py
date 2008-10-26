from nose.tools import with_setup, assert_not_equals, assert_true, assert_equals, assert_false
import shutil, os.path
from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)
from bookworm.search import index, epubindexer, constants

bookworm.settings.SEARCH_ROOT = os.path.join(bookworm.settings.ROOT_PATH, 'search', 'tests', 'dbs')

username = 'testuser'
book_name = 'book'

def setup(self):
    pass

def teardown(self):
    if os.path.exists(bookworm.settings.SEARCH_ROOT):
        shutil.rmtree(bookworm.settings.SEARCH_ROOT)

class TestIndex(object):
        
    def test_create_user_database(self):
        index.create_user_database(username)
        assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username)))
            
    def test_delete_user_database(self):
        index.create_user_database(username)
        assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username)))
        index.delete_user_database(username)
        assert_false(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username)))

    def test_create_book_database(self):
        index.create_book_database(username, book_name)
        assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username, book_name)))

    def test_delete_book_database(self):
        index.create_book_database(username, book_name)
        assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username, book_name)))
        index.delete_book_database(username, book_name)
        assert_false(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username, book_name)))

    def test_create_search_document(self):
        data = 'this is some content'
        doc = index.create_search_document('1', 'hello', data, '2', 'this is a chapter_title')
        assert_equals(data, doc.get_data())
        assert_equals('1', doc.get_value(constants.SEARCH_BOOK_ID))

    def test_index_search_document(self):
        book_id = '1'
        data = 'This is some test content'
        #db = index.create_book_database(username, book_id)
        doc = index.create_search_document(book_id, 'hello', data, '2', 'this is a chapter_title')
        index.index_search_document(doc, data)

    def test_add_search_document(self):
        book_id = '1'
        data = 'This is some test content'
        db = index.create_book_database(username, book_id)
        doc = index.create_search_document(book_id, 'hello', data, '2', 'this is a chapter_title')
        index.add_search_document(db, doc)
        
class TestEpubIndex(object):
    pass

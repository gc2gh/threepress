from nose.tools import with_setup, assert_not_equals, assert_true, assert_equals, assert_false
import shutil, os.path, logging

from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)

from django.contrib.auth.models import User

from bookworm.search import index, epubindexer, constants, search
from bookworm.library.models import EpubArchive, HTMLFile

bookworm.settings.SEARCH_ROOT = os.path.join(bookworm.settings.ROOT_PATH, 'search', 'tests', 'dbs')

log = logging.getLogger('search.test-index')

username = 'testuser'
book_name = 'book'

test_data_dir = os.path.join(bookworm.settings.ROOT_PATH, 'search', 'tests', 'test-data')

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

    def test_get_searchable_content(self):
        f = open(os.path.join(test_data_dir, 'valid-xhtml.html')).read()
        paras = epubindexer.get_searchable_content(f)
        assert_not_equals(None, paras)
        assert_true(len(paras) > 0)
        assert_true('humane' in paras)
        assert_false('<p' in paras)

    def test_index_epub(self):
        epub_id = create_document()
        epub = EpubArchive.objects.get(id=epub_id)
        chapter = HTMLFile.objects.get(archive=epub)
        epubindexer.index_epub(username, epub, chapter)


class TestEpubSearch(object):
    def test_search(self):
        epub_id = create_document()
        epub = EpubArchive.objects.get(id=epub_id)
        chapter = HTMLFile.objects.get(archive=epub)
        epubindexer.index_epub(username, epub, chapter)
        results = search.search('content', username, book=epub)
        assert_not_equals(None, results)
        assert_true(len(results) > 0)
        content = ''.join([r.highlighted_content for r in results])
        assert_true('content' in content)
        assert_true('class="match"' in content)
        assert_false('foobar' in content)

def create_user(username=username):
    user = User.objects.get_or_create(username=username)[0]
    user.save()
    return user

def create_document(title='test', 
                    content='<p>This is some content</p>',
                    chapter_title='Chapter 1'):
    user = create_user()
    epub = EpubArchive(title=title,
                       owner=user)
    epub.save()
    html = HTMLFile(processed_content=content,
                    archive=epub,
                    title=chapter_title)
    html.save()
    return epub.id
        

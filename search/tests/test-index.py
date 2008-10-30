from nose.tools import with_setup, assert_not_equals, assert_true, assert_equals, assert_false
import shutil, os.path, logging

from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)

from django.contrib.auth.models import User
from library.models import EpubArchive, HTMLFile

import search.indexer as indexer
import search.epubindexer as epubindexer
import search.constants as constants
import search.results as results

bookworm.settings.SEARCH_ROOT = os.path.join(bookworm.settings.ROOT_PATH, 'search', 'tests', 'dbs')

log = logging.getLogger('search.test-index')

username = 'testuser'
book_name = 'book'

test_data_dir = os.path.join(bookworm.settings.ROOT_PATH, 'search', 'tests', 'test-data')


class TestIndex(object):
    def setup(self):
        pass
    
    def teardown(self):
        if os.path.exists(bookworm.settings.SEARCH_ROOT):
            shutil.rmtree(bookworm.settings.SEARCH_ROOT)

    def test_create_user_database(self):
        indexer.create_user_database(username)
        assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username)))
            
    def test_delete_user_database(self):
        indexer.create_user_database(username)
        assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username)))
        indexer.delete_user_database(username)
        assert_false(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username)))

    def test_create_book_database(self):
        indexer.create_book_database(username, book_name)
        assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username, book_name)))

    def test_delete_book_database(self):
        indexer.create_book_database(username, book_name)
        assert_true(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username, book_name)))
        indexer.delete_book_database(username, book_name)
        assert_false(os.path.exists(os.path.join(bookworm.settings.SEARCH_ROOT, username, book_name)))

    def test_create_search_document(self):
        data = 'this is some content'
        doc = indexer.create_search_document('1', 'hello', data, '2', 'this is a chapter_title')
        assert_equals(data, doc.get_data())
        assert_equals('1', doc.get_value(constants.SEARCH_BOOK_ID))

    def test_index_search_document(self):
        book_id = '1'
        data = 'This is some test content'
        doc = indexer.create_search_document(book_id, 'hello', data, '2', 'this is a chapter_title')
        indexer.index_search_document(doc, data)

    def test_add_search_document(self):
        book_id = '1'
        data = 'This is some test content'
        db = indexer.create_book_database(username, book_id)
        doc = indexer.create_search_document(book_id, 'hello', data, '2', 'this is a chapter_title')
        indexer.add_search_document(db, doc)
        
    def test_add_to_index(self):
        book_id = '1'
        data = 'This is some test content'
        doc = indexer.create_search_document(book_id, 'hello', data, '2', 'this is a chapter_title')
        i = indexer.index_search_document(doc, data)
        indexer.add_to_index(i, 'this is more content', weight=2)

    def test_add_to_search(self):
        book_id = '99'
        username2 = 'newuser'
        data = 'Hello world.  This is test content.  Also other words.'
        db = indexer.create_database(username2)
        doc = indexer.create_search_document(book_id, 'hello', data, '2', 'this is a chapter_title')
        i = indexer.index_search_document(doc, data)

        # DB should be empty now
        assert_equals(db.get_doccount(), 0)

        # Add the document
        indexer.add_search_document(db, doc)

        # Make sure our document in there
        assert_equals(db.get_doccount(), 1)

        terms = [t.term for t in db.allterms()]
        
        # There should be twice as many terms in there -- stemmed and unstemmed forms
        assert_true('test' in terms)

#        res = results.search('test', username2)
#        assert_equals(len(res), 1)

        res = results.search('more', username2)
        assert_equals(len(res), 0)

        indexer.add_to_index(i, 'this is more content', weight=2)
        res = results.search('more', username2)
        assert_equals(len(res), 1)
        res = results.search('some', username2)
        assert_equals(len(res), 1)
        
class TestEpubIndex(object):
    def setup(self):
        pass
    
    def teardown(self):
        if os.path.exists(bookworm.settings.SEARCH_ROOT):
            shutil.rmtree(bookworm.settings.SEARCH_ROOT)

    def test_get_searchable_content(self):
        '''Make sure we can handle all kinds of HTML content'''
        f = open(os.path.join(test_data_dir, 'valid-xhtml.html')).read()
        paras = epubindexer.get_searchable_content(f)
        assert_not_equals(None, paras)
        assert_true(len(paras) > 0)
        assert_true('humane' in paras)
        assert_false('<p' in paras)

        f = open(os.path.join(test_data_dir, 'valid-html.html')).read()
        paras = epubindexer.get_searchable_content(f)
        assert_not_equals(None, paras)
        assert_true(len(paras) > 0)
        assert_true('humane' in paras)
        assert_false('<p' in paras)

        f = open(os.path.join(test_data_dir, 'broken-html.html')).read()
        paras = epubindexer.get_searchable_content(f)
        assert_not_equals(None, paras)
        assert_true(len(paras) > 0)
        assert_true('humane' in paras)
        assert_false('<p' in paras)

        paras = epubindexer.get_searchable_content('')
        assert_equals('', paras)

    def test_index_epub(self):
        epub_id = create_document()
        epub = EpubArchive.objects.get(id=epub_id)
        assert_false(epub.indexed)
        chapter = HTMLFile.objects.get(archive=epub)
        epubindexer.index_epub(username, epub, chapter)

        epub = EpubArchive.objects.get(id=epub_id)
        assert_true(epub.indexed)
        
    def test_user_library(self):
        username1 = 'test_user_library'
        indexer.create_user_database(username)
        user = User(username=username1)
        user.save()
        create_document(title='test1', username=username1)        
        create_document(title='test2', username=username1)                
        create_document(title='test3', username=username1)         
        num_indexed = epubindexer.index_user_library(user)
        assert_equals(3, num_indexed)

    def test_get_stemmer(self):
        lang = 'english'
        stemmer = indexer.get_stemmer(lang)
        assert_true('english' in stemmer.get_description())

        lang = 'french'
        stemmer = indexer.get_stemmer(lang)
        assert_true('french' in stemmer.get_description())

        lang = 'de'
        stemmer = indexer.get_stemmer(lang)
        assert_true('german' in stemmer.get_description())

        lang = 'es-SP'
        stemmer = indexer.get_stemmer(lang)
        assert_true('spanish' in stemmer.get_description())

        lang = 'es_SP'
        stemmer = indexer.get_stemmer(lang)
        assert_true('spanish' in stemmer.get_description())

        # Unknown languages should stem to English
        lang = 'unknown'
        stemmer = indexer.get_stemmer(lang)
        assert_true('english' in stemmer.get_description())

class TestEpubSearch(object):
    def setup(self):
        pass
    
    def teardown(self):
        if os.path.exists(bookworm.settings.SEARCH_ROOT):
            shutil.rmtree(bookworm.settings.SEARCH_ROOT)


    def test_search(self):
        epub_id = create_document()
        epub = EpubArchive.objects.get(id=epub_id)
        chapter = HTMLFile.objects.get(archive=epub)
        epubindexer.index_epub(username, epub, chapter)
        res = results.search('content', username, book_id=epub_id)
        assert_not_equals(None, res)
        assert_true(len(res) == 1)
        content = ''.join([r.highlighted_content for r in res])
        assert_true('content' in content)
        assert_true('class="bw-match"' in content)
        assert_false('foobar' in content)

    def test_result_object(self):
        epub_id = create_document(title='test title', chapter_title='chapter one')
        epub = EpubArchive.objects.get(id=epub_id)
        chapter = HTMLFile.objects.get(archive=epub)
        epubindexer.index_epub(username, epub, chapter)
        res = results.search('content', username, book_id=epub_id)[0]
        assert_equals(res.title, 'test title')
        assert_equals(res.chapter_title, 'chapter one')
        assert_equals(res.id, epub_id)
        
    def test_search_user(self):
        f = open(os.path.join(test_data_dir, 'valid-xhtml.html')).read()
        epub_id1 = create_document(content=f,
                                   title='Epub 1')
        f2 = open(os.path.join(test_data_dir, 'valid-xhtml2.html')).read()
        epub_id2 = create_document(content=f2,
                                   title='Epub 2')

        epub1 = EpubArchive.objects.get(id=epub_id1)
        chapter1 = HTMLFile.objects.get(archive=epub1)
        epub2 = EpubArchive.objects.get(id=epub_id2)
        chapter2 = HTMLFile.objects.get(archive=epub2)

        epubindexer.index_epub(username, epub1, chapter1)
        epubindexer.index_epub(username, epub2, chapter2)
        
        res = results.search('the', username)
        assert_equals(len(res), 2)
        
        res = results.search('Kitty', username)
        assert_equals(len(res), 1)



def create_user(username=username):
    user = User.objects.get_or_create(username=username)[0]
    user.save()
    return user

def create_document(title='test', 
                    content='<p>This is some content</p>',
                    chapter_title='Chapter 1',
                    username='test'):
    user = create_user(username)
    epub = EpubArchive(title=title,
                       owner=user)
    epub.save()
    html = HTMLFile(processed_content=content,
                    archive=epub,
                    title=chapter_title)
    html.save()
    return epub.id
        

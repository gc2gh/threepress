from lxml.html.soupparser import fromstring
import logging, os.path
from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)
 
import bookworm.search.indexer as indexer
import bookworm.library.models as models

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('epubindexerer')

def index_user_library(user):
    '''Indexer all of the books in a user's library. Returns the
    number of books indexered.'''
    books = models.EpubArchive.objects.filter(owner=user)
    for b in books:
        index_epub(user.username, b)
    return len(books)
    
def index_epub(username, epub, chapter=None):
    '''Indexer parts of an epub book as a searchable document.
    If an HTMLFile object is passed, indexer only that chapter;
    otherwise indexer all chapters.'''
    book_id = epub.id
    book_title = epub.title
    chapters = []
    if chapter is None:
        chapters = [c for c in models.HTMLFile.objects.filter(archive=epub)]
    if chapter is not None:
        chapters.append(chapter)

    database = indexer.create_book_database(username, book_id)
    user_database = indexer.create_user_database(username)

    for c in chapters:
        content = c.render()
        clean_content = get_searchable_content(content)
        doc = indexer.create_search_document(book_id, book_title, clean_content,
                                           c.id, c.title)
        indexer.index_search_document(doc, clean_content)

        indexer.add_search_document(database, doc)
        indexer.add_search_document(user_database, doc)

def get_searchable_content(content):
    '''Returns the content of a chapter as a searchable field'''
    html = fromstring(content)
    temp_para = [ p.xpath('.//text()') for p in html.iter(tag='{http://www.w3.org/1999/xhtml}p')]

    if len(temp_para) == 0 or None in temp_para:
        temp_para = [ p.xpath('.//text()') for p in html.iter(tag='p')]
    paragraphs = []
    for p in temp_para:
        paragraphs.append(' '.join([i.strip().replace('\n',' ') for i in p]))
    return '\n'.join(paragraphs)

                                     
    

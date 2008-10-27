import os, logging, os.path, shutil
import xapian
from django.core.management import setup_environ
import bookworm.settings
import bookworm.search.constants as constants
setup_environ(bookworm.settings)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('index')

indexer = xapian.TermGenerator()
stemmer = xapian.Stem("english")
indexer.set_stemmer(stemmer)


def create_search_document(book_id, book_title, content, chapter_id, chapter_title='Untitled chapter', ns=''):
    doc = xapian.Document()
    doc.set_data(content)
    doc.add_value(constants.SEARCH_BOOK_ID, unicode(book_id))
    doc.add_value(constants.SEARCH_BOOK_TITLE, unicode(book_title))
    doc.add_value(constants.SEARCH_CHAPTER_ID, unicode(chapter_id))
    doc.add_value(constants.SEARCH_CHAPTER_TITLE, unicode(chapter_title))
    doc.add_value(constants.SEARCH_NAMESPACE, ns)
    return doc

def add_search_document(database, doc):
    database.add_document(doc)

def index_search_document(doc, content):
    indexer.set_document(doc)
    indexer.index_text(content)

def create_user_database(username):
    '''Create a database that will hold all of the search content for an entire user'''
    user_db = get_user_database_path(username)
    return xapian.WritableDatabase(user_db, xapian.DB_CREATE_OR_OPEN)

def delete_user_database(username):
    user_db = get_user_database_path(username)
    log.warn("Deleting user database at '%s'" % user_db)
    try:
        shutil.rmtree(user_db)
    except OSError,e:
        raise IndexingError(e)

def create_book_database(username, book_id):
    create_user_database(username)
    book_db = get_book_database_path(username, book_id)
    return xapian.WritableDatabase(book_db, xapian.DB_CREATE_OR_OPEN)    

def delete_book_database(username, book_id):
    book_db = get_book_database_path(username, book_id)
    log.warn("Deleting book database at '%s'" % book_db)
    shutil.rmtree(book_db)    

def get_database(username, book_id=None):
    if book_id:
        path = get_book_database_path(username, book_id)
    else:
        path = get_user_database_path(username)
    return xapian.Database(path)
        
def get_user_database_path(username):
    if not os.path.exists(bookworm.settings.SEARCH_ROOT):
        log.debug("Creating search root path at '%s'" % bookworm.settings.SEARCH_ROOT)
        os.mkdir(bookworm.settings.SEARCH_ROOT)
    return os.path.join(bookworm.settings.SEARCH_ROOT, username)

def get_book_database_path(username, book_id):
    user_db = get_user_database_path(username)
    book_db = os.path.join(user_db, str(book_id))
    return book_db

class IndexingError(Exception):
    pass

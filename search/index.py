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


def create_search_document(book_id, book_title, content, chapter_id, chapter_title=''):
    doc = xapian.Document()
    doc.set_data(content)
    doc.add_value(constants.SEARCH_BOOK_ID, book_id)
    doc.add_value(constants.SEARCH_BOOK_TITLE, book_title)
    doc.add_value(constants.SEARCH_CHAPTER_ID, chapter_id)
    doc.add_value(constants.SEARCH_CHAPTER_TITLE, chapter_title)
    return doc

def add_search_document(database, doc):
    database.add_document(doc)

def index_search_document(doc, content):
    indexer.set_document(doc)
    indexer.index_text(content)

def create_user_database(username):
    '''Create a database that will hold all of the search content for an entire user'''
    user_db = _user_database(username)
    log.debug("Creating user database at '%s'" % user_db)
    return xapian.WritableDatabase(user_db, xapian.DB_CREATE_OR_OPEN)

def delete_user_database(username):
    user_db = _user_database(username)
    log.warn("Deleting user database at '%s'" % user_db)
    shutil.rmtree(user_db)

def create_book_database(username, book_id):
    create_user_database(username)
    book_db = _book_database(username, book_id)
    return xapian.WritableDatabase(book_db, xapian.DB_CREATE_OR_OPEN)    

def delete_book_database(username, book_id):
    book_db = _book_database(username, book_id)
    log.warn("Deleting book database at '%s'" % book_db)
    shutil.rmtree(book_db)    

def _user_database(username):
    if not os.path.exists(bookworm.settings.SEARCH_ROOT):
        log.debug("Creating search root path at '%s'" % bookworm.settings.SEARCH_ROOT)
        os.mkdir(bookworm.settings.SEARCH_ROOT)
    return os.path.join(bookworm.settings.SEARCH_ROOT, username)

def _book_database(username, book_id):
    user_db = _user_database(username)
    book_db = os.path.join(user_db, book_id)
    return book_db

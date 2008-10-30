import os, logging, os.path, shutil
import xapian
from django.core.management import setup_environ
import bookworm.settings
import bookworm.search.constants as constants
setup_environ(bookworm.settings)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('search.indexer')

def create_search_document(book_id, book_title, content, chapter_id, chapter_title='Untitled chapter', ns='', author_name='', language='en'):
    doc = xapian.Document()
    doc.set_data(content)
    doc.add_value(constants.SEARCH_BOOK_ID, unicode(book_id))
    doc.add_value(constants.SEARCH_BOOK_TITLE, unicode(book_title))
    doc.add_value(constants.SEARCH_CHAPTER_ID, unicode(chapter_id))
    doc.add_value(constants.SEARCH_CHAPTER_TITLE, unicode(chapter_title))
    doc.add_value(constants.SEARCH_NAMESPACE, ns)
    doc.add_value(constants.SEARCH_AUTHOR_NAME, unicode(author_name))
    doc.add_value(constants.SEARCH_LANGUAGE_VALUE, unicode(language))
    return doc

def add_search_document(database, doc):
    database.add_document(doc)

def index_search_document(doc, content, weight=1):
    '''Create a new index and stemmer from the given document, 
    run the index, and return the indexer'''
    indexer = xapian.TermGenerator()
    stemmer = get_stemmer(doc.get_value(constants.SEARCH_LANGUAGE_VALUE))
    log.debug("Using stemmer %s" % stemmer.get_description())

    indexer.set_stemmer(stemmer)
    indexer.set_document(doc)
    indexer.index_text(content, weight)
    return indexer

def add_to_index(indexer, content, weight=1):
    '''Add one or more terms to an existing index.'''
    indexer.index_text(content, weight)
    return indexer

def get_stemmer(lang_value):
    '''Converts from a variety of language values into a
    supported stemmer'''
    if '-' in lang_value:
        # We only want the first part in a multi-value lang, e.g. 'en' in 
        # 'en-US'
        language = lang_value.split('-')[0]
    elif '_' in lang_value:
        language = lang_value.split('_')[0]
    else:
        language = lang_value
    try:
        stemmer = xapian.Stem(language)    
    except xapian.InvalidArgumentError:
        log.warn("Got unknown language value '%s'; going to default lang '%s'" % 
                 (lang_value, constants.DEFAULT_LANGUAGE_VALUE))
        stemmer = xapian.Stem(constants.DEFAULT_LANGUAGE_VALUE)
    return stemmer
    
def create_user_database(username):
    '''Create a database that will hold all of the search content for an entire user'''
    user_db = get_user_database_path(username)
    log.debug("Creating user database at '%s'" % user_db)
    return xapian.WritableDatabase(user_db, xapian.DB_CREATE_OR_OPEN)

def delete_user_database(username):
    user_db = get_user_database_path(username)
    log.warn("Deleting user database at '%s'" % user_db)
    try:
        shutil.rmtree(user_db)
    except OSError,e:
        raise IndexingError(e)

def create_database(username, book_id=None):
    if book_id:
        return create_book_database(username, book_id)
    return create_user_database(username)

def create_book_database(username, book_id):
    create_user_database(username)
    book_db = get_book_database_path(username, book_id)
    log.debug("Creating book database at '%s'" % book_db)
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
    log.debug("Returning database at '%s'" % path)
    try:
        db = xapian.Database(path)
    except xapian.DatabaseOpeningError:
        # We should have a database, but we don't.  This will
        # end up with no results, but create one anyway
        # because that's better than an exception.
        db = create_database(username, book_id)
    return db

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

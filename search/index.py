from lxml import etree
import os, sys, logging, subprocess, os.path, shutil
import xapian
from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('index')

indexer = xapian.TermGenerator()
stemmer = xapian.Stem("english")
indexer.set_stemmer(stemmer)

def create_user_database(username):
    '''Create a database that will hold all of the search content for an entire user'''
    user_db = _user_database(username)
    log.debug("Creating user database at '%s'" % user_db)
    return xapian.WritableDatabase(user_db, xapian.DB_CREATE_OR_OPEN)

def delete_user_database(username):
    user_db = _user_database(username)
    log.warn("Deleting user database at '%s'" % user_db)
    shutil.rmtree(user_db)

def create_epub_database(username, epub_id):
    create_user_database(username)
    book_db = _epub_database(username, epub_id)
    return xapian.WritableDatabase(book_db, xapian.DB_CREATE_OR_OPEN)    

def delete_epub_database(username, epub_id):
    book_db = _epub_database(username, epub_id)
    log.warn("Deleting epub database at '%s'" % book_db)
    shutil.rmtree(book_db)    

def _user_database(username):
    if not os.path.exists(bookworm.settings.SEARCH_ROOT):
        log.debug("Creating search root path at '%s'" % bookworm.settings.SEARCH_ROOT)
        os.mkdir(bookworm.settings.SEARCH_ROOT)
    return os.path.join(bookworm.settings.SEARCH_ROOT, username)

def _epub_database(username, epub_id):
    user_db = _user_database(username)
    book_db = os.path.join(user_db, epub_id)
    return book_db

import lxml
from lxml.html.soupparser import fromstring
import os, sys, logging, subprocess, os.path, shutil
import xapian
from django.core.management import setup_environ
import bookworm.settings
setup_environ(bookworm.settings)

import bookworm.search.constants as constants
import bookworm.search.index as index
import bookworm.library.models as models

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('epubindexer')

def index_user_library(user):
    '''Index all of the books in a user's library. Returns the
    number of books indexed.'''
    books = models.EpubArchive.objects.filter(owner=user)
    for b in books:
        index_epub(user.username, b)
    return len(books)
    


def index_epub(username, epub, chapter=None):
    '''Index parts of an epub book as a searchable document.
    If an HTMLFile object is passed, index only that chapter;
    otherwise index all chapters.'''
    book_id = epub.id
    book_title = epub.title
    chapters = []
    if chapter is None:
        chapters = [c for c in models.HTMLFile.objects.filter(archive=epub)]
    if chapter is not None:
        chapters.append(chapter)

    database = index.create_book_database(username, book_id)
    user_database = index.create_user_database(username)

    for c in chapters:
        content = c.render()
        clean_content = get_searchable_content(content)
        doc = index.create_search_document(book_id, book_title, clean_content,
                                           c.id, c.title)
        index.index_search_document(doc, clean_content)

        index.add_search_document(database, doc)
        index.add_search_document(user_database, doc)

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

                                     
    

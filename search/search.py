import os, logging, os.path, shutil
import xapian
from django.core.management import setup_environ
import bookworm.settings
import bookworm.search.constants as constants
from bookworm.search import index

setup_environ(bookworm.settings)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('index')

indexer = xapian.TermGenerator()
stemmer = xapian.Stem("english")
indexer.set_stemmer(stemmer)


def search(term, username, book=None, start=1, end=constants.RESULTS_PAGESIZE, sort='ordinal'):
    database = index.get_database(username, book.id)

    # Start an enquire session.
    enquire = xapian.Enquire(database)
    # Parse the query string to produce a Xapian::Query object.
    qp = xapian.QueryParser()
    qp.set_stemmer(stemmer)
    qp.set_database(database)
    qp.set_stemming_strategy(xapian.QueryParser.STEM_SOME)
    query = qp.parse_query(term)
    log.debug("Parsed query is: %s" % query.get_description())

    enquire.set_query(query)

    set_start = 0 if start == 1 else start

    if sort == constants.SORT_ORDINAL:
        enquire.set_sort_by_value(constants.SEARCH_ORDINAL, False)

    matches = enquire.get_mset(set_start, end, 101)

    # Display the results.
    estimate = matches.get_matches_estimated()

    size = matches.size()
    if size < end - start:
        end = start + size
    next_end = end + constants.RESULTS_PAGESIZE

    show_previous = True if start != 1 else False
    show_next = True if end < estimate else False
    
    next_start = start + constants.RESULTS_PAGESIZE

    previous_start = start - constants.RESULTS_PAGESIZE
    previous_end = previous_start + constants.RESULTS_PAGESIZE

    results = [Result(match.docid, match.document) for match in matches]
    for r in results:
        words = []
        for word in r.xapian_document.get_data().split(" "):
            term = word.replace('?', '').replace('"', '').replace('.', '').replace(',', '')
            term = term.lower()
            for t in enquire.matching_terms(r.id):
                if "Z%s" % stemmer(term) == t or term == t:
                    word = '<span class="match">%s</span>' % word
            words.append(word)

        r.highlighted_content = ' '.join(words)
        print r.highlighted_content

    return results


class Result:
    highlighted_content = None
    def __init__(self, id, xapian_document):
        self.id = id
        self.document_id = int(xapian_document.get_value(constants.SEARCH_BOOK_ID))
        self.xapian_document = xapian_document
        self.title = xapian_document.get_value(constants.SEARCH_BOOK_TITLE)

    def get_chapter_id(self):
        return self.xapian_document.get_value(constants.SEARCH_CHAPTER_ID)

    def get_book_title(self):
        return self.xapian_document.get_value(constants.SEARCH_BOOK_TITLE)

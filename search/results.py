import os, logging, os.path, shutil
from lxml.html import soupparser
from lxml import etree
import xapian

from django.core.management import setup_environ
import bookworm.settings
from django.core.urlresolvers import reverse

from django.utils.http import urlquote_plus

import bookworm.search.constants as constants
from bookworm.search import index

setup_environ(bookworm.settings)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('index')

indexer = xapian.TermGenerator()
stemmer = xapian.Stem("english")
indexer.set_stemmer(stemmer)


def search(term, username, book_id=None, start=1, end=constants.RESULTS_PAGESIZE, sort='ordinal'):
    database = index.get_database(username, book_id)

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
        terms = set(enquire.matching_terms(r.xapian_id))
        for word in r.xapian_document.get_data().split(" "):
            term = word.replace('?', '').replace('"', '').replace('.', '').replace(',', '')
            term = term.lower()
            if "Z%s" % stemmer(term) in terms or term in terms:
                word = '<%s class="%s">%s</span>' % (constants.RESULT_ELEMENT, constants.RESULT_ELEMENT_CLASS, word)
            words.append(word)
        
        r.set_content(' '.join(words))
    return results


class Result(object):
    highlighted_content = None
    def __init__(self, xapian_id, xapian_document):
        self.xapian_id = xapian_id
        self.xapian_document = xapian_document
        self.parsed_content = None
        self.highlighted_content = None

    @property
    def id(self):
        return int(self.xapian_document.get_value(constants.SEARCH_BOOK_ID))

    @property
    def title(self):
        return self.xapian_document.get_value(constants.SEARCH_BOOK_TITLE)

    @property
    def chapter_id(self):
        return self.xapian_document.get_value(constants.SEARCH_CHAPTER_ID)

    @property
    def chapter_title(self):
        return self.xapian_document.get_value(constants.SEARCH_CHAPTER_TITLE)

    @property
    def namespace(self):
        ns = self.xapian_document.get_value(constants.SEARCH_NAMESPACE)
        if ns:
            ns = '{%s}' % ns
        return ns

    @property
    def url(self):
        return reverse('view_chapter', args=[urlquote_plus(self.title), str(self.id), str(self.chapter_id)])

    def set_content(self, content):
        self.highlighted_content = content
        self.parsed_content = soupparser.fromstring(content)

    @property
    def result_fragment(self):
        match = self.parsed_content.xpath("(//%s%s[@class='%s'])[1]" % (self.namespace, constants.RESULT_ELEMENT, constants.RESULT_ELEMENT_CLASS))[0]
        out = []
        text_preceding = match.xpath('preceding::text()[1]')
        if len(text_preceding) > 0:
            preceding = text_preceding[0].split(' ')
            preceding.reverse()
            length = constants.RESULT_WORD_BREAKS if len(preceding) > constants.RESULT_WORD_BREAKS else len(preceding)
            temp = []
            for word in preceding[0:length]:
                temp.append(word)
            temp.reverse()
            for word in temp:
                out.append(word)
        out.append('<%s class="%s">%s</span>' % (constants.RESULT_ELEMENT,
                                                 constants.RESULT_ELEMENT_CLASS,
                                                 match.text))

        text_following = match.xpath('following::text()[1]')
        if len(text_following) > 0:
            following = text_following[0].split(' ')
            length = constants.RESULT_WORD_BREAKS if len(following) > constants.RESULT_WORD_BREAKS else len(following)
            for word in following[0:length]:
                out.append(word)
        return ' '.join(out)




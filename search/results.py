import os, logging, os.path, shutil
from lxml.html import soupparser
from lxml import etree

from django.core.management import setup_environ
import bookworm.settings

from django.utils.http import urlquote_plus

import bookworm.search.constants as constants
setup_environ(bookworm.settings)

log = logging.getLogger('search.results')

class Result(object):
    highlighted_content = None

    def __init__(self, htmlfile, search_term):
        self.htmlfile = htmlfile
        self.search_term = search_term
        self.set_content(htmlfile.processed_content)

    @property
    def id(self):
        return self.htmlfile.archive.id

    @property
    def title(self):
        return self.htmlfile.archive.title

    @property
    def chapter_id(self):
        return self.htmlfile.id

    @property
    def chapter_title(self):
        if self.htmlfile.title is not None or self.htmlfile.title != '':
            return self.htmlfile.title
        return self.htmlfile.filename
        return self.parsed_content.xpath('//title/text()')[0]

    @property
    def chapter_filename(self):
        return self.htmlfile.filename

    @property
    def author(self):
        return self.htmlfile.archive.author

    @property
    def language(self):
        return self.htmlfile.archive.get_major_language

    @property
    def url(self):
        return self.htmlfile.get_absolute_url()

    def set_content(self, content):
        self.highlighted_content = content
        self.parsed_content = soupparser.fromstring(content)

    @property
    def result_fragment(self):
        for p in self.parsed_content.iter(tag='p'):
            words = [w for w in ' '.join((w.lower() for w in p.xpath('text()'))).split(' ')]
            if self.search_term.lower() in words:
                return etree.tostring(p)
    @property
    def old_result_fragment(self):
        match_expression = self.parsed_content.xpath("(//%s%s[@class='%s'])[1]" % (self.namespace, constants.RESULT_ELEMENT, constants.RESULT_ELEMENT_CLASS))
        if len(match_expression) == 0:
            # We didn't find a match; for now don't show captioning
            # fixme later to improve term matching
            return self.parsed_content
        match = match_expression[0]
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




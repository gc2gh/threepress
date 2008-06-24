# -*- coding: utf-8 -*-
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from StringIO import StringIO
import logging, datetime, sys
from urllib import unquote_plus
from xml.parsers.expat import ExpatError
import htmlentitydefs
import cssutils
import base64

from django.utils.http import urlquote_plus
from django.db import models
from django.db.models import permalink
from django.contrib.auth.models import User
from django.utils.encoding import smart_str

from epub import constants, InvalidEpubException
from epub.constants import ENC, BW_BOOK_CLASS
from epub.constants import NAMESPACES as NS
from epub.toc import NavPoint, TOC


# Functions
def safe_name(name):
    '''Return a name that can be used safely in a URL'''
    quote = urlquote_plus(name.encode(ENC))
    return quote
 
def unsafe_name(name):
    '''Convert from a URL-formatted name to something that will match
    in the datastore'''
    unquote = unquote_plus(name.encode(ENC))
    return unicode(unquote, ENC)

def encode_content(c):
    return base64.b64encode(c)
def decode_content(c):
    return base64.b64decode(c)

class BookwormModel(models.Model):
    '''Base class for all models'''
    created_time = models.DateTimeField('date created', default=datetime.datetime.now())
    def key(self):
        '''Backwards compatibility with templates'''
        return self.id

    class Meta:
        abstract = True

class EpubArchive(BookwormModel):
    '''Represents an entire epub container'''

    _CONTAINER = constants.CONTAINER     

    _archive = None
    _parsed_metadata = None
    _parsed_toc = None

    name = models.CharField(max_length=2000)
    owner = models.ForeignKey(User)
    authors = models.ManyToManyField('BookAuthor')

    title = models.CharField(max_length=5000)
    _content = models.TextField()  # will have to base64-encode this; Django has no blob field, wtf
    opf = models.TextField()
    toc = models.TextField()
    has_stylesheets = models.BooleanField(default=False)

    def get_content(self):
        return decode_content(self._content)
    def set_content(self, c):
        self._content = encode_content(c)

    def author(self):
        '''This method returns the author, if only one, or the first author in
        the list with ellipses for additional authors.'''
        if not self.authors:
            return None
        a = self.authors.all()
        if len(a) == 0:
            return ''
        if len(a) == 1:
            return a[0].name
        return a[0].name + '...'

    def _get_metadata(self, metadata_tag, opf):
        '''Returns a metdata item's text content by tag name, or a list if mulitple names match'''
        if not self._parsed_metadata:
            self._parsed_metadata = self._xml_from_string(opf)
        text = []
        for t in self._parsed_metadata.findall('.//{%s}%s' % (NS['dc'], metadata_tag)):
            text.append(t.text)
        if len(text) == 1:
            return text[0]
        return text

    def get_subjects(self):
        return self._get_metadata(constants.DC_SUBJECT_TAG, self.opf)
    
    def get_rights(self):
        return self._get_metadata(constants.DC_RIGHTS_TAG, self.opf)

    def get_language(self):
        '''@todo expand into full form '''
        return self._get_metadata(constants.DC_LANGUAGE_TAG, self.opf)        

    def get_publisher(self):
        return self._get_metadata(constants.DC_PUBLISHER_TAG, self.opf)

    def get_top_level_toc(self):
        t = self._get_parsed_toc()
        return t.find_points()

    def _get_parsed_toc(self):
        if not self._parsed_toc:
            self._parsed_toc = TOC(self.toc)
        return self._parsed_toc
        
        
    def explode(self):
        '''Explodes an epub archive'''
        e = StringIO(self.get_content())
        z = ZipFile(e)

        logging.debug(z.namelist())
        self._archive = z

        try:
            container = z.read(self._CONTAINER)
        except KeyError:
            raise InvalidEpubException()

        parsed_container = self._xml_from_string(container)

        opf_filename = self._get_opf_filename(parsed_container)

        content_path = self._get_content_path(opf_filename)

        self.opf = unicode(z.read(opf_filename), ENC)
        parsed_opf = self._xml_from_string(self.opf.encode(ENC))
        
        items = parsed_opf.getiterator("{%s}item" % (NS['opf']))

        self.toc = unicode(z.read(self._get_toc(parsed_opf, items, content_path)), ENC)

        parsed_toc = self._xml_from_string(self.toc.encode(ENC))



        self.authors = self._get_authors(parsed_opf)
        self.title = self._get_title(parsed_opf) 

        self._get_content(parsed_opf, parsed_toc, items, content_path)
        self._get_stylesheets(items, content_path)
        self._get_images(items, content_path)


    def _xml_from_string(self, xml):
        return ET.fromstring(xml)

    def _get_opf_filename(self, container):
        '''Parse the container to get the name of the opf file'''
        return container.find('.//{%s}rootfile' % NS['container']).get('full-path')

    def _get_content_path(self, opf_filename):
        '''Return the content path, which may be a named subdirectory or could be at the root of
        the archive'''
        paths = opf_filename.split('/')
        if len(paths) == 1:
            # We have no extra path info; this document's content is at the root
            return ''
        else:
            return paths[0] + '/'
 
    def _get_toc(self, opf, items, content_path):
        '''Parse the opf file to get the name of the TOC
        (From OPF spec: The spine element must include the toc attribute, 
        whose value is the the id attribute value of the required NCX document 
        declared in manifest)'''
        tocid = opf.find('.//{%s}spine' % NS['opf']).get('toc')
        for item in items:
            if item.get('id') == tocid:
                toc_filename = item.get('href').strip()
                logging.debug('Got toc filename as %s' % toc_filename)
                return "%s%s" % (content_path, toc_filename)
        raise Exception("Could not find toc filename")

    def _get_authors(self, opf):
        authors = [BookAuthor(name=unicode(a.text.strip(), ENC)) for a in opf.findall('.//{%s}%s' % (NS['dc'], constants.DC_CREATOR_TAG))]
        if len(authors) == 0:
            logging.warn('Got empty authors string for book %s' % self.name)
        else:
            logging.info('Got authors as %s' % (authors))
        for a in authors:
            a.save()
        return authors

    def _get_title(self, xml):
        title = xml.findtext('.//{%s}%s' % (NS['dc'], constants.DC_TITLE_TAG)).strip()
        logging.info('Got title as %s' % (title))
        return title

    def _get_images(self, items, content_path):
        '''Images might be in a variety of formats, from JPEG to SVG.'''
        images = []
        for item in items:
            if 'image' in item.get('media-type'):
                
                content = self._archive.read("%s%s" % (content_path, item.get('href')))
                data = {}
                data['data'] = None
                data['file'] = None
 
                if item.get('media-type') == constants.SVG_MIMETYPE:
                    logging.debug('Adding image as SVG text type')
                    data['file'] = unicode(content, ENC)

                else:
                    # This is a binary file, like a jpeg
                    logging.debug('Adding image as binary type')
                    data['data'] = content

                data['idref'] = item.get('href')
                data['content_type'] = item.get('media-type')

                images.append(data)

                logging.debug('adding image %s ' % item.get('href'))

        self._create_images(images)                

    def _create_images(self, images):
        for i in images:
            f = i['file']
            if f == None:
                f = ''
            image = ImageFile(
                              idref=i['idref'],
                              file=f,
                              content_type=i['content_type'],
                              archive=self)
            image.set_data(i['data'])
            image.save()  

    def _get_stylesheets(self, items, content_path):
        stylesheets = []
        for item in items:
            if item.get('media-type') == constants.STYLESHEET_MIMETYPE:
                content = self._archive.read("%s%s" % (content_path, item.get('href')))
                parsed_content = self._parse_stylesheet(content)
                stylesheets.append({'idref':item.get('href'),
                                    'file':unicode(parsed_content, ENC)})


                logging.debug('adding stylesheet %s ' % item.get('href'))
                self.has_stylesheets = True
        self._create_stylesheets(stylesheets)

    def _parse_stylesheet(self, stylesheet):
        css = cssutils.parseString(stylesheet)
        for rule in css.cssRules:
            try:
                for selector in rule._selectorList:
                    if 'body' in selector.selectorText:
                        # Replace the body tag with a generic div, so the rules
                        # apply even though we've stripped out <body>
                        selector.selectorText = selector.selectorText.replace('body', 'div')
                    selector.selectorText = BW_BOOK_CLASS + ' ' + selector.selectorText 
                    
            except AttributeError:
                pass # (was not a CSSStyleRule)
        return css.cssText

    def _create_stylesheets(self, stylesheets):
        for s in stylesheets:
            css = StylesheetFile(
                                 idref=s['idref'],
                                 file=s['file'],
                                 archive=self)
            css.save()            

 
    def _get_content(self, opf, toc, items, content_path):
        # Get all the item references from the <spine>
        refs = opf.getiterator('{%s}itemref' % (NS['opf']) )
        navs = [n for n in toc.getiterator('{%s}navPoint' % (NS['ncx']))]
        navs2 = [n for n in toc.getiterator('{%s}navTarget' % (NS['ncx']))]
        navs = navs + navs2

        nav_map = {}
        item_map = {}
        
        metas = toc.getiterator('{%s}meta' % (NS['ncx']))
      
        for m in metas:
            if m.get('name') == 'db:depth':
                depth = int(m.get('content'))
                logging.debug('Book has depth of %d' % depth)
        
        for item in items:
            item_map[item.get('id')] = item.get('href')
             
        for nav in navs:
            n = NavPoint(nav, doc_title=self.title)
            href = n.href()
            filename = href.split('#')[0]
            
            if nav_map.has_key(filename):
                pass
                # Skip this item so we don't overwrite with a new navpoint
            else:
                logging.debug('adding filename %s to navmap' % filename)
                nav_map[filename] = n

        pages = []

        for ref in refs:
            idref = ref.get('idref')
            if item_map.has_key(idref):
                href = item_map[idref]
                logging.debug("checking href %s" % href)
                if nav_map.has_key(href):
                    logging.debug('Adding navmap item %s' % nav_map[href])
                    filename = '%s%s' % (content_path, href)
                    content = self._archive.read(filename)
                    
                    # We store the raw XHTML and will process it for display on request
                    # later
                    page = {'title': nav_map[href].title(),
                            'idref':href,
                            'file':content,
                            'archive':self,
                            'order':nav_map[href].order()}
                    pages.append(page)
                    
        self._create_pages(pages)


    def _create_pages(self, pages):
        for p in pages:
            self._create_page(p['title'], p['idref'], p['file'], p['archive'], p['order'])

    def _create_page(self, title, idref, f, archive, order):
        '''Create an HTML page and associate it with the archive'''
        html = HTMLFile(
                        title=title, 
                        idref=unicode(idref, ENC),
                        file=unicode(f, ENC),
                        archive=archive,
                        order=order)
        html.save()
 
                  
    def safe_title(self):
        '''Return a URL-safe title'''
        return safe_name(self.title)  

    def safe_author(self):
        '''We only use the first author name for our unique identifier, which should be
        good enough for all but the oddest cases (revisions?)'''
        if self.authors:
            return safe_name(self.authors[0])
        return None

    class Admin:
        pass

class BookAuthor(BookwormModel):
    name = models.CharField(max_length=2000)
    def __str__(self):
        return self.name
    class Admin:
        pass

class BookwormFile(BookwormModel):
    '''Abstract class that represents a file in the database'''
    idref = models.CharField(max_length=1000)
    file = models.TextField(default='')    
    archive = models.ForeignKey(EpubArchive)

    def render(self):
        return self.file
    class Meta:
        abstract = True

class HTMLFile(BookwormFile):
    '''Usually an individual page in the ebook'''
    title = models.CharField(max_length=5000)
    order = models.PositiveSmallIntegerField(default=1)
    processed_content = models.TextField()
    content_type = models.CharField(max_length=100, default="application/xhtml")

    def render(self):
        '''If we don't have any processed content, process it and cache the
        results in the datastore.'''
        if self.processed_content:
            return self.processed_content
        
        logging.debug('Parsing body content for first display')
        f = smart_str(self.file, encoding=ENC)

        src = StringIO(f)
        try:
            xhtml = CleanXmlFile(file=src)
        except ExpatError:
            logging.error('Was not valid XHTML; treating as uncleaned string')
            self.processed_content = f
            return f

        body = xhtml.find('{%s}body' % NS['html'])
        body = self._clean_xhtml(body)
        div = ET.Element('div')
        div.attrib['id'] = 'bw-book-content'
        children = body.getchildren()
        for c in children:
            div.append(c)
        body_content = ET.tostring(div, ENC)

        try:
            self.processed_content = unicode(body_content, ENC)
            self.save()            
        except: 
            logging.error("Could not cache processed document, error was: " + sys.exc_info()[0])

        return body_content

    def _clean_xhtml(self, xhtml):
        '''This is only run the first time the user requests the HTML file; the processed HTML is then cached'''
        
        parent_map = dict((c, p) for p in xhtml.getiterator() for c in p)

        for element in xhtml.getiterator():
            element.tag = element.tag.replace('{%s}' % NS['html'], '')

            # if we have SVG, then we need to re-write the image links that contain svg in order to
            # make them work in most browsers
            if element.tag == 'img' and 'svg' in element.get('src'):
                logging.debug('translating svg image %s' % element.get('src'))
                try:
                    p = parent_map[element]
                    logging.debug("Got parent %s " % (p.tag)) 

                    e = ET.fromstring("""
<a class="svg" href="%s">[ View linked image in SVG format ]</a>
""" % element.get('src'))
                    p.remove(element)
                    p.append(e)
                    logging.debug("Added subelement %s to %s " % (e.tag, p.tag)) 
                except: 
                    logging.error("ERROR:" + sys.exc_info())[0]
        return xhtml
    def __str__(self):
        return "[%d] '%s' in %s " % (self.order, self.title, self.archive.title)

    class Admin:
        pass
    class Meta:
        ordering = ['order']
class StylesheetFile(BookwormFile):
    '''A CSS stylesheet associated with a given book'''
    content_type = models.CharField(max_length=100, default="text/css")
    class Admin:
        pass

class ImageFile(BookwormFile):
    '''An image file associated with a given book.  Mime-type will vary.'''
    content_type = models.CharField(max_length=100)
    _data = models.TextField(null=True) # really base64

    def get_data(self):
        return decode_content(self._data)
    def set_data(self, d):
        self._data = encode_content(d)

    class Admin:
        pass

class UserPref(BookwormModel):
    '''Per-user preferences for this application'''
    user = models.ForeignKey(User, unique=True)
    use_iframe = models.BooleanField(default=False)
    show_iframe_note = models.BooleanField(default=True)
    class Admin:
        pass

class SystemInfo():
    '''This can now be computed at runtime (and cached)'''
    # @todo create methods for these
    def __init__(self):
        self._total_books = None
        self._total_users = None

    def get_total_books(self):
        if not self._total_books:
            self._total_books = EpubArchive.objects.count()
        return self._total_books

    def get_total_users(self):
        if not self._total_users:
            self._total_users = UserPref.objects.count()
        return self._total_users

    def increment_total_books(self):
        t = self.get_total_books()
        self._total_books += 1

    def decrement_total_books(self):
        t = self.get_total_books()
        if t > 0:
            self._total_books += 1

    def increment_total_users(self):
        t = self.get_total_users()
        self._total_users += 1

    def decrement_total_users(self):
        t = self.get_total_users()
        if t > 0:
            self._total_users += 1



class CleanXmlFile(ET.ElementTree):
    '''Implementation that includes all HTML entities'''
    def __init__(self, file=None, tag='global', **extra):
        ET.ElementTree.__init__(self) 
        parser = ET.XMLTreeBuilder(
            target=ET.TreeBuilder(ET.Element)) 
        parser.entity = htmlentitydefs.entitydefs
        self.parse(source=file, parser=parser) 
        return



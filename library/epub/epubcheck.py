import urllib, logging
from lxml import etree
from django.conf import settings
from bookworm.library.epub import toc
from django.utils.translation import ugettext as _

log = logging.getLogger(__name__)

# Functions that work with the epubcheck service

def validate(data, fail_silently=True):
    '''Sends a value of data to the epubcheck validation service at threepress.org and parses the response.
    `data` should be an epub as a stream of bytes.

    By default, exceptions are ignored (the service may be down).

    Returns either True if the file is valid, or a list of errors if the file is not valid.
    '''
    resp = urllib.urlopen(settings.EPUBCHECK_WEBSERVICE, data)
    try:
        epubcheck_response =  toc.xml_from_string(resp.read())
        if epubcheck_response.findtext('.//is-valid') == 'True':
            return True
        elif epubcheck_response.findtext('.//is-valid') == 'False':
            return epubcheck_response.findall('.//error')
    except Exception, e:
        if fail_silently:
            log.warn("Failure during epubcheck: %s" % e)
        else:
            raise e

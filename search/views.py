from django.core.mail import EmailMessage

import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.core.paginator import Paginator, EmptyPage
from django.views.generic.simple import direct_to_template
from django.conf import settings

import results
import epubindexer

log = logging.getLogger('search.views')

@login_required
def search(request, book_id=None):
    res = None
    if 'q' in request.GET:
        term = request.GET['q']
        res = results.search(term, request.user.username, book_id)
    return direct_to_template(request, 'results.html', 
                              { 'results':res, })

@login_required
def index(request, book_id=None):
    '''Forceaably index a user's books.  The user can only index
    their own books; this will generally be used for testing only.'''
    index_user_library(request.user)
    

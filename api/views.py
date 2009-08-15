from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseNotAllowed
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.generic.simple import direct_to_template
from django.core.urlresolvers import reverse

from bookworm.library import models 
from bookworm.library.views import download_epub, add_by_url_field

@never_cache
@login_required
def api_list(request, SSL=True):
    '''List the user's library'''
    if request.method != 'GET':
        return HttpResponseNotAllowed('GET')

    documents = models.EpubArchive.objects.filter(user_archive__user=request.user).order_by(settings.DEFAULT_ORDER_FIELD).distinct()
    return direct_to_template(request, 'api/list.html', 
                              {'documents': documents})
    
@never_cache
@login_required
def api_download(request, epub_id, SSL=True):
    '''Download an epub file by its ID'''
    if request.method != 'GET':
        return HttpResponseNotAllowed('GET')

    return download_epub(request, '', epub_id)

@never_cache
@login_required
def api_upload(request, SSL=True):
    '''Accept an epub file either by URL or by direct POST upload with epub bytes'''
    if request.method != 'POST':
        return HttpResponseNotAllowed('POST')

    if 'epub_url' in request.POST:
        resp = add_by_url_field(request, request.POST['epub_url'], redirect_success_to_page=False)        
        if isinstance(resp, models.EpubArchive):
            # This was a successful add and we got back a document
            httpresp = HttpResponse()
            httpresp.status_code = 201
            httpresp['Location'] = reverse('api_download', args=[resp.id])
            return httpresp
        # Otherwise this was an error condition
        httpresp = HttpResponse(resp) # Include the complete Bookworm response
        httpresp.status_code = 500 # FIXME pick a useful status code
        return httpresp
    elif 'epub_data' in request.POST:
        pass
    raise Http404

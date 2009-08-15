from django.conf import settings
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.generic.simple import direct_to_template

from bookworm.library import models 
from bookworm.library.views import download_epub

@never_cache
@login_required
def api_list(request, SSL=True):
    '''List the user's library'''
    documents = models.EpubArchive.objects.filter(user_archive__user=request.user).order_by(settings.DEFAULT_ORDER_FIELD).distinct()
    return direct_to_template(request, 'api/list.html', 
                              {'documents': documents})
    
@never_cache
@login_required
def api_download(request, epub_id, SSL=True):
    '''Download an epub file by its ID'''
    return download_epub(request, '', epub_id)

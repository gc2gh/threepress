import logging

from forms import EpubSearchForm
from library.models import EpubArchive

log = logging.getLogger('context_processors')

def count_books(user):
    return EpubArchive.objects.filter(owner=user).count()
 
def search(request):
    form = None
    current_search_language = None
    if (not request.user.is_anonymous()) and count_books(request.user) > 0:
        form = EpubSearchForm()
        if 'q' in request.GET:
            form = EpubSearchForm(request.GET)
        if 'language' in request.GET:
            current_search_language = request.GET['language']
        
    return {'search_form': form,
            'current_search_language': current_search_language}
    

import logging

from forms import EpubSearchForm
from library.models import EpubArchive

log = logging.getLogger('context_processors')

def count_books(user):
    return EpubArchive.objects.filter(owner=user).count()
 
def search(request):

    if count_books(request.user) > 0:
        form = EpubSearchForm()
    else:
        form = None
    return {'search_form': form }
    

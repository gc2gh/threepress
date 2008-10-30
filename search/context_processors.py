import logging

from forms import EpubSearchForm
from library.models import EpubArchive

log = logging.getLogger('context_processors')

def count_books(user):
    return EpubArchive.objects.filter(owner=user).count()
 
def search(request):
    form = None
    if (not request.user.is_anonymous()) and count_books(request.user) > 0:
        form = EpubSearchForm()
    return {'search_form': form }
    

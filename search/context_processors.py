import logging
from django.conf import settings

from forms import EpubSearchForm
from library.models import EpubArchive


log = logging.getLogger('context_processors')

def count_books(user):
    return EpubArchive.objects.filter(user_archive__user=user).distinct().count()
 
def search(request):
    form = None
    current_search_language = 'English'
    form = EpubSearchForm()
    return {'search_form': form,
            'current_search_language': current_search_language}
    

def _get_name_for_language(lang):
    for l in settings.LANGUAGES:
        if lang == l[0]:
            return l[1]
    return lang

import logging
from django.conf import settings

from forms import EpubSearchForm
from library.models import EpubArchive


log = logging.getLogger('context_processors')

def count_books(user):
    return EpubArchive.objects.filter(owner=user).count()
 
def search(request):
    form = None
    current_search_language = 'english'
    if (not request.user.is_anonymous()) and count_books(request.user) > 0:
        if 'language' in request.GET:
            current_search_language = request.GET['language']
        elif request.user.get_profile().language is not None:
            current_search_language = _get_name_for_language(request.user.get_profile().language)
        else:
            if 'language_name' in request.session:
                current_search_language = request.session.get('language_name')
            else:
                current_search_language = _get_name_for_language(request.session.get(settings.LANGUAGE_COOKIE_NAME))
                request.session.set('language_name', current_search_language)

        if 'q' in request.GET:
            form = EpubSearchForm(request.GET, lang=current_search_language)
        else:
            form = EpubSearchForm(lang=current_search_language)

    return {'search_form': form,
            'current_search_language': current_search_language}
    

def _get_name_for_language(lang):
    for l in settings.LANGUAGES:
        if lang == l[0]:
            return l[1]
    return lang

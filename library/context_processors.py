import logging
from forms import EpubValidateForm
from models import SystemInfo
from django.conf import settings

log = logging.getLogger('context_processors')
 
def nav(request):
    form = EpubValidateForm()
    return {'upload_form': form }

def common(request):
    common = {}
    common['user'] = request.user
    common['is_admin'] = request.user.is_superuser
    common['prefs'] = _prefs(request)
    common['total_users'] = _get_system_info(request).get_total_users()
    common['total_books'] = _get_system_info(request).get_total_books()
    common['mobile'] = settings.MOBILE 

    return { 'common': common }

def _get_system_info(request):
    '''Super-primitive caching system'''
    if not 'system_info' in request.session:
        request.session['system_info'] = SystemInfo()
    return request.session['system_info']

def _prefs(request):
    '''Get (or create) a user preferences object for a given user.
    If created, the total number of users counter will be incremented and
    the memcache updated.'''
    user = request.user
    try:
        userprefs = user.get_profile()
    except AttributeError:
        # Occurs when this is called on an anonymous user; ignore
        return None
    except UserPref.DoesNotExist:
        log.debug('Creating a userprefs object for %s' % user.username)
        # Create a preference object for this user
        userprefs = UserPref(user=user)
        userprefs.save()

        # Increment our total-users counter
        counter = _get_system_info(request)

        counter.increment_total_users()
  
    return userprefs

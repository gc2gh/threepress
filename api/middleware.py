# The following license information applies to the SSL Redirect class.  All other code
# is licensed under the Bookworm license

__license__ = "Python"
__copyright__ = "Copyright (C) 2007, Stephen Zabel"
__author__ = "Stephen Zabel - sjzabel@gmail.com"
__contributors__ = "Jay Parlar - parlar@gmail.com"

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect, get_host
from django.contrib.auth import login, authenticate

from bookworm.api import models 

SSL = 'SSL'


class APIKeyCheck(object):

    def process_view(self, request, view_func, view_args, view_kwargs):

        if SSL in view_kwargs and not '/public/' in request.path: # This could be improved
            if settings.API_FIELD_NAME in request.GET:
                apikey = request.GET[settings.API_FIELD_NAME]
            elif settings.API_FIELD_NAME in request.POST:
                apikey = request.GET[settings.API_FIELD_NAME]
            else:
                raise models.APIException("api_key was not found in request parameters")
            user = models.APIKey.objects.user_for_key(apikey)
            user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user)
            return None

class SSLRedirect(object):
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        '''Redirect the view to SSL if the SSL parameter is true AND if we are neither in 
        debug mode (using the Django development server) nor running tests (via test_settings.py)'''
        if SSL in view_kwargs and not (settings.TESTING or settings.DEBUG):
            secure = view_kwargs[SSL]
            del view_kwargs[SSL]
        else:
            secure = False

        if not secure == self._is_secure(request):
            return self._redirect(request, secure)

    def _is_secure(self, request):
        if request.is_secure():
	    return True

        #Handle the Webfaction case until this gets resolved in the request.is_secure()
        if 'HTTP_X_FORWARDED_SSL' in request.META:
            return request.META['HTTP_X_FORWARDED_SSL'] == 'on'

        return False

    def _redirect(self, request, secure):
        protocol = secure and "https" or "http"
        newurl = "%s://%s%s" % (protocol,get_host(request),request.get_full_path())
        if settings.DEBUG and request.method == 'POST':
            raise RuntimeError, \
        """Django can't perform a SSL redirect while maintaining POST data.
           Please structure your views so that redirects only occur during GETs."""

        return HttpResponsePermanentRedirect(newurl)

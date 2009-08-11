from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('bookworm.api.views',
                       url(r'^$', 'api', name="api"),                        
)

urlpatterns += patterns('django.views.generic.simple',
                        url(r'^help/$', 'direct_to_template', {'template': 'api_help.html'}, name='api_help'),
                        )

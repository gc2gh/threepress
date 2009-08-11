from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('bookworm.api.views',
                       url(r'^list/$', 'api_list', {'SSL':True}, name="api_list"),
)

urlpatterns += patterns('django.views.generic.simple',
                        url(r'^public/help/$', 'direct_to_template', {'template': 'api_help.html'}, name='api_help'),
                        )

from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('bookworm.api.views',
                       url(r'^documents/$', 'api_list', {'SSL':True}, name="api_list"),
                       url(r'^documents/(?P<epub_id>\d+)/$', 'api_download', {'SSL':True}, name="api_download"),
                       url(r'^upload/$', 'api_upload', {'SSL':True}, name="api_upload"),
)

urlpatterns += patterns('django.views.generic.simple',
                        url(r'^public/help/$', 'direct_to_template', {'template': 'api_help.html'}, name='api_help'),
                        )

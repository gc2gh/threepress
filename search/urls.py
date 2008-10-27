from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('search.views',
                       url(r'^$', 'index', name="index"),                        
)

urlpatterns += patterns('django.views.generic.simple',
                        url(r'^help$', 'direct_to_template',
                            {'template': 'help.html'}, name='help'),
                        )

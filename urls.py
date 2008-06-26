from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib.sitemaps import FlatPageSitemap
from django.contrib.auth.views import login, logout

sitemaps = {
    'flatpages' : FlatPageSitemap,
}

urlpatterns = patterns('',

                       # Uncomment this for admin:
                       (r'^admin/', include('django.contrib.admin.urls')),

                       # Sitemaps
                       (r'^sitemap.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
                       
                       # Auth
                       (r'^account/', include('django_authopenid.urls')),                       
                       
#                        (r'^accounts/login/$',  login, {'template_name': 'auth/openid_signin.html'}),
#                        (r'^accounts/logout/$', logout, {'next_page': '/openid/signout/'}),
#                        (r'^accounts/register/$', 'library.views.register'),

#                        # OpenID
#                        (r'^accounts/login/openid/$', 'django_openidconsumer.views.begin', 
#                         {'sreg': 'email,nickname,fullname,country,language,timezone'},
#                         ),
#                        (r'^openid/complete/$', 'django_openidauth.views.complete', 
#                         {'on_login_ok_url'    : '/',
#                          'on_login_failed_url': '/accounts/register/'
#                          }),
#                        (r'^openid/signout/$', 'django_openidconsumer.views.signout'),
#                        (r'^openid/associations/$', 'django_openidauth.views.associations'),

#                        (r'^openid/register/$', 'django_openidauth.regviews.register', 
#                         {'success_url': '/'
#                          }),
#                        (r'^accounts/login/complete/$', 'django_openidconsumer.views.complete'),
#                        (r'^accounts/login/signout/$', 'django_openidconsumer.views.signout'),                       
                       
                       # Bookworm
                       (r'^$', 'library.views.index'),                        
                       
                       (r'^upload/$', 'library.views.upload'),

                       # Images from within documents
                       (r'^(view|chapter)/(?P<title>[^/]+)/(?P<key>[^/]+)/(?P<image>.*(jpg|gif|png|svg)+)$', 
                        'library.views.view_chapter_image'),                       

                       # View a chapter in frame mode
                       (r'^chapter/(?P<title>.+)/(?P<key>.+)/(?P<chapter_id>.+)$', 'library.views.view_chapter_frame'),                       

                       # View a chapter in non-frame mode
                       (r'^view/(?P<title>.+)/(?P<key>.+)/(?P<chapter_id>.+)$', 'library.views.view_chapter'),                       
                       
                       # Main entry point for a document
                       (r'^view/(?P<title>.+)/(?P<key>[^/]+)/$', 'library.views.view'),

                       # CSS file for within a document (frame-mode)
                       (r'^css/(?P<title>[^/]+)/(?P<key>[^/]+)/(?P<stylesheet_id>.+)$', 'library.views.view_stylesheet'),                       

                       (r'^delete/', 'library.views.delete'),
                       
                       # Download a source epub file
                       (r'^download/epub/(?P<title>.+)/(?P<key>[^/]+)/$', 'library.views.download_epub'),

                       # User profile
                       (r'^accounts/profile/$', 'library.views.profile'),
                       
                       (r'^accounts/profile/delete/$', 'library.views.profile_delete'),

                       # Static pages
                       (r'^about/$', 'library.views.about'),

                       # Admin pages
                       (r'^admin/search/$', 'library.admin.search'),

                       )


if settings.DEBUG:
    urlpatterns += patterns('',
                            (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH + '/library/templates/static'}),
                            )
    

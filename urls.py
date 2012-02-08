from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
#from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
	url(r'^$', 'mdb.views.home', name='home'),
	url(r'^info/', include('mdb.urls')),
	url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()


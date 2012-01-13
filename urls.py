from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'mdb.views.home', name='home'),

    (r'^admin/', include(admin.site.urls)),
)

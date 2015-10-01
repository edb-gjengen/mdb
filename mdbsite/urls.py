from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView
from mdb.api.views import ValidatePuppetHostSecret

admin.autodiscover()

urlpatterns = [
    url(r'^$', RedirectView.as_view(url='admin/')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/validate-host-secret', ValidatePuppetHostSecret.as_view(), name='api-validate-host-secret')
]

urlpatterns += staticfiles_urlpatterns()

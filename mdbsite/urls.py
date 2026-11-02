from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path
from django.views.generic.base import RedirectView

from mdb.api.views import HostPXEValidate

admin.autodiscover()

urlpatterns = [
    path("", RedirectView.as_view(url="admin/", permanent=True)),
    path("admin/", admin.site.urls),
    path(
        "api/validate-host-secret/",
        HostPXEValidate.as_view(),
        name="api-validate-host-secret",
    ),
]

urlpatterns += staticfiles_urlpatterns()

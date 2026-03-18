import os

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("billing/", include("apps.billing.urls")),
    path("sync/", include("apps.sync.urls")),
]

if os.environ.get("AZURE_CLIENT_ID"):
    urlpatterns.insert(1, path("oauth2/", include("django_auth_adfs.urls")))

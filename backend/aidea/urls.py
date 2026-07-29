"""
URL configuration for aidea project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.static import serve

urlpatterns = [
    # Django admin lives under /django-admin/ so the SPA can own /admin/* for
    # its own Admin Panel routes (e.g. /admin/users) without the reverse proxy
    # sending those refreshes to Django.
    path('django-admin/', admin.site.urls),
    path('api/', include('hub.urls')),
    path('api/analytics/', include('analytics.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        # Media files are lesson content (e.g. PDFs) meant to be embedded in the
        # SPA's iframes, which run on a different origin/port — exempt clickjacking
        # protection for this path only so XFrameOptionsMiddleware doesn't block them.
        re_path(
            r'^media/(?P<path>.*)$',
            xframe_options_exempt(serve),
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]

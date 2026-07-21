"""
URL configuration for iot_portal project.

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
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from catalogue.forms import LoginForm
from catalogue.views import custom_admin_login, CustomLoginView, CustomSignupView


def serve_sw(request):
    import os
    sw_path = os.path.join(settings.BASE_DIR.parent, 'sw.js')
    with open(sw_path, 'rb') as f:
        content = f.read()
    response = HttpResponse(content, content_type='application/javascript')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


urlpatterns = [
    re_path(r'^admin/$', lambda request: redirect('/dashboard/') if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser) else (redirect('user_dashboard') if request.user.is_authenticated else redirect('custom_admin_login'))),
    path('admin/login/', custom_admin_login, name='custom_admin_login'),
    path('admin/', admin.site.urls),
    path('accounts/login/', CustomLoginView.as_view(authentication_form=LoginForm), name='login'),
    path('accounts/signup/', CustomSignupView.as_view(), name='account_signup'),
    path('accounts/', include('allauth.urls')),
    path('', include('catalogue.urls')),
    re_path(r'^sw\.js$', serve_sw),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

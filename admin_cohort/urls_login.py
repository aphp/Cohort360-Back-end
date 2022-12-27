"""cohort_back URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.contrib.auth import views
from django.urls import re_path
from rest_framework.routers import DefaultRouter

from admin_cohort.views import CustomLoginView, redirect_token_refresh_view

router = DefaultRouter()

app_name = 'rest_framework'
urlpatterns = [re_path(r'^login/$', CustomLoginView.as_view(template_name='login.html'), name='login'),
               re_path(r'^refresh/$', redirect_token_refresh_view, name='token_refresh'),
               re_path(r'^logout/$', views.LogoutView.as_view(), name='logout')
               ]

from django.urls import re_path

from admin_cohort.views import JWTLoginView, token_refresh_view, LogoutView

# router = DefaultRouter()
# router.register(r'', AuthViewSet, basename="auth")
# urlpatterns = [path('', include(router.urls))]

app_name = 'rest_framework'
urlpatterns = [re_path(r'^login/$', JWTLoginView.as_view(template_name='login.html'), name='login'),
               re_path(r'^refresh/$', token_refresh_view, name='token_refresh'),
               re_path(r'^logout/$', LogoutView.as_view(), name='logout')
               ]

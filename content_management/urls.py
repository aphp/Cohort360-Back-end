from django.urls import path, include

from admin_cohort.urls import NestedDefaultRouter
from .views import ContentViewSet

router = NestedDefaultRouter()
router.register(r'contents', ContentViewSet, basename="contents")

urlpatterns = [
    path('', include(router.urls)),
]

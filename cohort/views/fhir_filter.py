from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from admin_cohort.tools.cache import cache_response
from cohort.models import FhirFilter
from cohort.serializers import FhirFilterSerializer


class FhirFilterViewSet(viewsets.ModelViewSet):
    queryset = FhirFilter.objects.all()
    serializer_class = FhirFilterSerializer
    pagination_class = LimitOffsetPagination
    swagger_tags = ["Cohort - fhir_filter"]
    filter_backends = [SearchFilter]
    search_fields = ("filter_name", 'fhir_resource')

    @action(detail=False, methods=['GET'])
    def recent_filters(self, request):
        filters = FhirFilter.objects.filter(owner=request.user).order_by('-created_at')
        serializer = FhirFilterSerializer(filters, many=True)
        return Response(serializer.data)

    @cache_response()
    def list(self, request, *args, **kwargs):
        """Method added only to have it cached, it only calls the super class with the input."""
        return super(FhirFilterViewSet, self).list(request, *args, **kwargs)
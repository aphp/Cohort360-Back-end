from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from cohort.models import FhirFilter
from cohort.serializers import FhirFilterSerializer


class FhirFilterViewSet(viewsets.ModelViewSet):
    queryset = FhirFilter.objects.all()
    serializer_class = FhirFilterSerializer
    pagination_class = LimitOffsetPagination
    swagger_tags = ["Cohort - fhir_filter"]
    search_fields = ("$name",)

    @action(detail=False, methods=['GET'])
    def recent_filters(self, request):
        filters = FhirFilter.objects.filter(owner=request.user).order_by('-created_at')
        serializer = FhirFilterSerializer(filters, many=True)
        return Response(serializer.data)

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from accesses.models import Perimeter
from accesses_fhir_perimeters.perimeters_updater import update_perimeter, perimeters_data_model_objects_update
from admin_cohort.permissions import MaintenancesPermission


class FhirPerimeterResultSerializer(serializers.Serializer):
    request_job_status = serializers.CharField(required=True)
    group_id = serializers.CharField(required=True)
    group_count = serializers.CharField(required=True)

    def update(self, instance, validated_data):
        return instance

    def to_internal_value(self, data):
        for field in ("group_id", "group_count"):
            if field in data:
                dotted_field = field.replace("_", ".")
                data[dotted_field] = data.pop(field)
        return super().to_internal_value(data)


class FhirPerimeterResult(GenericViewSet):
    swagger_tags = ['Fhir Perimeters - Cohort Result']
    permission_classes = (MaintenancesPermission,)
    http_method_names = ['put', 'patch']
    lookup_field = "id"
    queryset = Perimeter.objects.all()
    serializer_class = FhirPerimeterResultSerializer

    @extend_schema(summary="Used by sjs to update cohort status",
                   responses={status.HTTP_200_OK: OpenApiTypes.STR,
                              status.HTTP_400_BAD_REQUEST: OpenApiTypes.STR})
    def partial_update(self, request, *args, **kwargs):
        perimeter = self.get_object()
        group_id = request.data.get("group.id")
        group_count = request.data.get("group.count")
        update_perimeter(perimeter, group_id, group_count)
        return Response(data={}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        raise NotImplementedError("Update method is not allowed")

    @extend_schema(
        summary="Syncs the perimeters with fhir Organization and Encounter resources",
        request=None,
        responses={status.HTTP_200_OK: None, status.HTTP_500_INTERNAL_SERVER_ERROR: None})
    @action(detail=False, methods=['put'], url_path="_sync")
    def update_perimeters(self, request, *args, **kwargs):
        perimeters_data_model_objects_update()
        return Response(data=None, status=status.HTTP_200_OK)

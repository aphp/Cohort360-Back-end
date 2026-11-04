from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from accesses.models import Perimeter
from accesses_fhir_perimeters.perimeters_updater import perimeters_data_model_objects_update
from accesses_fhir_perimeters.permissions import FhirPerimeterResultPermission


class FhirPerimeterResult(GenericViewSet):
    swagger_tags = ["Fhir Perimeters - Sync"]
    permission_classes = (FhirPerimeterResultPermission,)
    http_method_names = ["put"]
    queryset = Perimeter.objects.all()

    @extend_schema(
        summary="Syncs the perimeters with fhir Organization and List resources",
        request=None,
        responses={status.HTTP_200_OK: None, status.HTTP_500_INTERNAL_SERVER_ERROR: None},
    )
    @action(detail=False, methods=["put"], url_path="_sync")
    def update_perimeters(self, request, *args, **kwargs):
        perimeters_data_model_objects_update()
        return Response(data=None, status=status.HTTP_200_OK)

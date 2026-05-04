from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_cohort.services.health import run_health_checks


class HealthView(APIView):
    http_method_names = ["get"]
    authentication_classes: list = []
    permission_classes = [AllowAny]
    serializer_class = None
    queryset = None

    @extend_schema(
        tags=["Health"],
        description="Liveness/readiness endpoint exposing the status of Django and its external dependencies. "
        "Returns 200 when the backend is operational (status `ok` or `degraded`) and 503 when at least one "
        "critical dependency is unreachable from Django.",
        auth=[],
    )
    def get(self, request, *args, **kwargs):
        report = run_health_checks()
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE if report["status"] == "ko" else status.HTTP_200_OK
        return Response(data=report, status=http_status)

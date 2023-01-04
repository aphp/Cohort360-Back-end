import urllib
from functools import reduce

from django.db.models import Q, BooleanField, When, Case, Value, \
    QuerySet
from django.db.models.functions import Coalesce
from django.http import Http404
from django.utils import timezone
from django_filters import OrderingFilter
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AND
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN

from admin_cohort.permissions import IsAuthenticated
from admin_cohort.settings import PERIMETERS_TYPES
from admin_cohort.tools import join_qs
from admin_cohort.views import BaseViewset, CustomLoggingMixin
from ..models import Role, Access, get_user_valid_manual_accesses_queryset, \
    intersect_queryset_criteria, build_data_rights
from ..permissions import AccessPermissions
from ..serializers import AccessSerializer, DataRightSerializer


class AccessFilter(filters.FilterSet):
    def target_perimeter_filter(self, queryset, field, value):
        if value:
            return queryset.filter((join_qs([Q(**{'perimeter' + i * '__children': value})
                                             for i in range(1, len(PERIMETERS_TYPES))])
                                    & Role.impact_lower_levels_query('role'))
                                   | Q(perimeter=value))
        return queryset

    provider_email = filters.CharFilter(lookup_expr="icontains", field_name="profile__email")
    provider_lastname = filters.CharFilter(lookup_expr="icontains", field_name="profile__lastname")
    provider_firstname = filters.CharFilter(lookup_expr="icontains", field_name="profile__firstname")
    provider_source_value = filters.CharFilter(lookup_expr="icontains", field_name="profile__user_id")
    provider_id = filters.CharFilter(field_name="profile__provider_id")
    provider_history_id = filters.CharFilter(field_name="profile_id")

    profile_email = filters.CharFilter(lookup_expr="icontains", field_name="profile__email")
    profile_lastname = filters.CharFilter(lookup_expr="icontains", field_name="profile__lastname")
    profile_firstname = filters.CharFilter(lookup_expr="icontains", field_name="profile__firstname")
    profile_user_id = filters.CharFilter(lookup_expr="icontains", field_name="profile__user__pk")
    profile_id = filters.CharFilter(field_name="profile_id")

    perimeter_name = filters.CharFilter(field_name="perimeter__name", lookup_expr="icontains")
    care_site_id = filters.CharFilter(field_name="perimeter_id")
    # perimeter_id = filters.CharFilter(method="perimeter_id_filter")

    target_care_site_id = filters.CharFilter(method="target_perimeter_filter")
    target_perimeter_id = filters.CharFilter(method="target_perimeter_filter")

    ordering = OrderingFilter(fields=(('role__name', 'role_name'),
                                      ('sql_start_datetime', 'start_datetime'),
                                      ('sql_end_datetime', 'end_datetime'),
                                      ('sql_is_valid', 'is_valid')))

    class Meta:
        model = Access
        fields = ("profile_email", "provider_email",
                  "profile_lastname", "provider_lastname",
                  "profile_firstname", "provider_firstname",
                  "profile_user_id", "provider_source_value",
                  "provider_id", "profile_id", "provider_history_id",
                  "perimeter", "care_site_id",
                  "target_perimeter_id", "target_care_site_id")


class AccessViewSet(CustomLoggingMixin, BaseViewset):
    serializer_class = AccessSerializer
    queryset = Access.objects.all()
    lookup_field = "id"

    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    swagger_tags = ['Accesses - accesses']

    search_fields = ["profile__lastname",
                     "profile__firstname",
                     "perimeter__name",
                     "profile__email",
                     "profile__user__provider_username"]
    filterset_class = AccessFilter

    def get_permissions(self):
        if self.action in ['my_accesses', 'data_rights']:
            return [IsAuthenticated()]
        return [AND(IsAuthenticated(), AccessPermissions())]

    def get_queryset(self) -> QuerySet:
        q = super(AccessViewSet, self).get_queryset()
        user = self.request.user
        if not user.is_anonymous:
            accesses = user.valid_manual_accesses_queryset.select_related("role")
        else:
            accesses = []
        to_exclude = [a.accesses_criteria_to_exclude for a in accesses]
        if to_exclude:
            to_exclude = reduce(intersect_queryset_criteria, to_exclude)
            qs = []
            for cs in to_exclude:
                exc_q = Q(**dict((f'role__{r}', v)
                                 for (r, v) in cs.items()
                                 if 'perimeter' not in r))
                if 'perimeter_not' in cs:
                    exc_q = exc_q & ~Q(perimeter_id__in=cs['perimeter_not'])
                if 'perimeter_not_child' in cs:
                    exc_q = exc_q & ~join_qs([Q(**{f"perimeter__{i * 'parent__'}id__in": (cs['perimeter_not_child'])})
                                              for i in range(1, len(PERIMETERS_TYPES))])

                qs.append(exc_q)
            q = qs and q.exclude(join_qs(qs)) or q
        return q

    def filter_queryset(self, queryset):
        now = timezone.now()
        queryset = queryset.annotate(sql_start_datetime=Coalesce('manual_start_datetime', 'start_datetime'),
                                     sql_end_datetime=Coalesce('manual_end_datetime', 'end_datetime')
                                     ).annotate(sql_is_valid=Case(When(sql_start_datetime__lte=now,
                                                                       sql_end_datetime__gte=now,
                                                                       then=Value(True)),
                                                                  default=Value(False),
                                                                  output_field=BooleanField()
                                                                  )
                                                )
        return super(AccessViewSet, self).filter_queryset(queryset)

    @swagger_auto_schema(manual_parameters=list(map(lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY,
                                                                                description=x[1], type=x[2],
                                                                                pattern=x[3] if len(x) == 4 else None),
                                                    [["perimeter_id", "Filter type", openapi.TYPE_STRING],
                                                     ["target_perimeter_id", "Filter type. Used to also get accesses on"
                                                                             " parents of this perimeter",
                                                      openapi.TYPE_STRING],
                                                     ["profile_email", "Search type", openapi.TYPE_STRING],
                                                     ["profile_name", "Search type", openapi.TYPE_STRING],
                                                     ["profile_lastname", "Search type", openapi.TYPE_STRING],
                                                     ["profile_firstname", "Search type", openapi.TYPE_STRING],
                                                     ["profile_user_id", "Search type", openapi.TYPE_STRING,
                                                      r'\d{1,7}'],
                                                     ["profile_id", "Filter type", openapi.TYPE_STRING],
                                                     ["search", "Will search in multiple fields (perimeter_name, "
                                                                "provider_name, lastname, firstname, "
                                                                "provider_source_value, email)", openapi.TYPE_STRING],
                                                     ["ordering", "To sort the result. Can be care_site_name, "
                                                                  "role_name, start_datetime, end_datetime, is_valid. "
                                                                  "Use -field for descending order",
                                                      openapi.TYPE_STRING]])))
    def list(self, request, *args, **kwargs):
        return super(AccessViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"provider_history_id": openapi.Schema(type=openapi.TYPE_INTEGER,
                                                          description="(to deprecate -> profile_id) Correspond à "
                                                                      "Provider_history_id"),
                    "profile_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Correspond à un profile_id"),
                    "care_site_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="2deprecate -> perimeter_id"),
                    "perimeter_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "role_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "start_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                     description="Doit être dans le futur.\nSi vide ou null, sera "
                                                                 "défini à now().\nDoit contenir la timezone ou bien "
                                                                 "sera considéré comme UTC."),
                    "end_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                   description="Doit être dans le futur. \nSi vide ou null, sera "
                                                               "défini à start_datetime + 1 un an.\nDoit contenir la "
                                                               "timezone ou bien sera considéré comme UTC.")},
        required=['profile', 'perimeter', 'role']))
    def create(self, request, *args, **kwargs):
        if "care_site_id" not in request.data and 'perimeter_id' not in request.data:
            return Response({"response": "perimeter_id is required"}, status=status.HTTP_404_NOT_FOUND)
        request.data['profile_id'] = request.data.get('profile_id', request.data.get('provider_history_id'))
        request.data['perimeter_id'] = request.data.get('perimeter_id', request.data.get('care_site_id'))
        return super(AccessViewSet, self).create(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        return super(AccessViewSet, self).dispatch(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"start_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                     description="Doit être dans le futur.\nNe peut pas être modifié "
                                                                 "si start_datetime actuel est déja passé.\nSera mis à "
                                                                 "now() si null.\nDoit contenir la timezone ou bien "
                                                                 "sera considéré comme UTC."),
                    "end_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                   description="Doit être dans le futur.\nNe peut pas être modifié si "
                                                               "end_datetime actuel est déja passé.\nNe peut pas être "
                                                               "mise à null.\nDoit contenir la timezone ou bien sera "
                                                               "considéré comme UTC.")}))
    def partial_update(self, request, *args, **kwargs):
        return super(AccessViewSet, self).partial_update(request, *args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def update(self, request, *args, **kwargs):
        return super(AccessViewSet, self).update(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_STRING, properties={}),
                         method="PATCH",
                         operation_summary="Will set end_datetime to now, to close the access.")
    @action(url_path="close", detail=True, methods=['patch'], permission_classes=(IsAuthenticated,))
    def close(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.actual_end_datetime:
            if instance.actual_end_datetime < timezone.now():
                return Response("L'accès est déjà clôturé.", status=status.HTTP_403_FORBIDDEN)

        if instance.actual_start_datetime:
            if instance.actual_start_datetime > timezone.now():
                return Response("L'accès n'a pas encore commencé, il ne peut pas être déjà fermé."
                                "Il peut cependant être supprimé, avec la méthode DELETE.",
                                status=status.HTTP_403_FORBIDDEN)

        request.data.update({'end_datetime': timezone.now()})
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.actual_start_datetime:
            if instance.actual_start_datetime < timezone.now():
                return Response("L'accès est déjà/a déjà été activé, il ne peut plus être supprimé.",
                                status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_object(self):
        if self.request.method == "GET":
            try:
                obj = super(AccessViewSet, self).get_object()
            except PermissionDenied:
                raise Http404
            except Exception as e:
                raise e
        else:
            obj = super(AccessViewSet, self).get_object()
        return obj

    @swagger_auto_schema(method='get', operation_summary="Get the authenticated user's valid accesses.")
    @action(url_path="my-accesses", detail=False, methods=['get'])
    def my_accesses(self, request, *args, **kwargs):
        q = get_user_valid_manual_accesses_queryset(self.request.user)
        serializer = self.get_serializer(q, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(operation_description="Returns particular type of objects, describing the data rights that a "
                                               "user has on a care-sites. AT LEAST one parameter is necessary",
                         manual_parameters=[i for i in map(lambda x: openapi.Parameter(
                             name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                             pattern=x[3] if len(x) == 4 else None),
                                                           [["care-site-ids", "(to deprecate -> perimeters_ids) List "
                                                                              "of care-sites to limit the result on. "
                                                                              "Sep: ','", openapi.TYPE_STRING],
                                                            ["perimeters_ids", "List of perimeters to limit the result "
                                                                               "on. Sep: ','", openapi.TYPE_STRING],
                                                            ["pop-children", "2deprecate(pop_children) If True, keeps "
                                                                             "only the biggest parents for each right",
                                                             openapi.TYPE_BOOLEAN],
                                                            ["pop_children", "If True, keeps only the biggest parents "
                                                                             "for each right", openapi.TYPE_BOOLEAN]])],
                         responses={200: openapi.Response('Rights found', DataRightSerializer),
                                    403: openapi.Response('perimeters_ids and pop_children are both null')})
    @action(url_path="my-rights", detail=False, methods=['get'], filter_backends=[], pagination_class=None)
    def data_rights(self, request, *args, **kwargs):
        param_perimeters = self.request.GET.get('perimeters_ids', self.request.GET.get('care-site-ids'))
        pop_children = self.request.GET.get('pop_children', self.request.GET.get('pop-children'))
        if param_perimeters is None and pop_children is None:
            return Response("Cannot have both 'perimeters-ids/care-site-ids' and 'pop-children' at null "
                            "(would return rights on all Perimeters).",
                            status=HTTP_403_FORBIDDEN)
        user = self.request.user
        # if the result is asked only for a list of perimeters,
        # we start our search on these
        if param_perimeters:
            urldecode_perimeters = urllib.parse.unquote(urllib.parse.unquote((str(param_perimeters))))
            required_cs_ids = [int(i) for i in urldecode_perimeters.split(",")]
        else:
            required_cs_ids = []

        results = build_data_rights(user, required_cs_ids, pop_children)
        return Response(data=DataRightSerializer(results, many=True).data,
                        status=status.HTTP_200_OK)

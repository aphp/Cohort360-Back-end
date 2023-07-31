import urllib
from datetime import date, timedelta
from functools import reduce

from django.db.models import Q, BooleanField, When, Case, Value, QuerySet
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
from rest_framework.response import Response

from admin_cohort.permissions import IsAuthenticated
from admin_cohort.settings import PERIMETERS_TYPES, ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS
from admin_cohort.tools import join_qs
from admin_cohort.tools.cache import cache_response
from admin_cohort.views import BaseViewset, CustomLoggingMixin
from ..models import Access, get_user_valid_manual_accesses, intersect_queryset_criteria, build_data_rights
from ..permissions import AccessPermissions
from ..serializers import AccessSerializer, DataRightSerializer, ExpiringAccessesSerializer


class AccessFilter(filters.FilterSet):
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

    ordering = OrderingFilter(fields=(('role__name', 'role_name'),
                                      ('sql_start_datetime', 'start_datetime'),
                                      ('sql_end_datetime', 'end_datetime'),
                                      ('sql_is_valid', 'is_valid')))

    class Meta:
        model = Access
        fields = ("perimeter",)


class AccessViewSet(CustomLoggingMixin, BaseViewset):
    serializer_class = AccessSerializer
    queryset = Access.objects.all()
    lookup_field = "id"
    filterset_class = AccessFilter
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    swagger_tags = ['Accesses - accesses']
    search_fields = ["profile__lastname",
                     "profile__firstname",
                     "perimeter__name",
                     "profile__email",
                     "profile__user__provider_username"]

    def get_permissions(self):
        if self.action in ['my_accesses', 'my_rights']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), AccessPermissions()]

    def get_serializer_class(self):
        if self.request.method == "GET" and "expiring" in self.request.query_params:
            return ExpiringAccessesSerializer
        return self.serializer_class

    def get_queryset(self) -> QuerySet:
        q = super(AccessViewSet, self).get_queryset()
        user = self.request.user
        if not user.is_anonymous:
            accesses = get_user_valid_manual_accesses(user).select_related("role")
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
                                     sql_end_datetime=Coalesce('manual_end_datetime', 'end_datetime'))\
                           .annotate(sql_is_valid=Case(When(sql_start_datetime__lte=now,
                                                            sql_end_datetime__gte=now,
                                                            then=Value(True)),
                                                       default=Value(False),
                                                       output_field=BooleanField()))
        return super(AccessViewSet, self).filter_queryset(queryset)

    def get_object(self):
        if self.request.method == "GET":
            try:
                obj = super(AccessViewSet, self).get_object()
            except (Http404, PermissionDenied):
                raise Http404
        else:
            obj = super(AccessViewSet, self).get_object()
        return obj

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
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(AccessViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"provider_history_id": openapi.Schema(type=openapi.TYPE_INTEGER,
                                                          description="(to deprecate -> profile_id) Correspond à Provider_history_id"),
                    "profile_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Correspond à un profile_id"),
                    "care_site_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="2deprecate -> perimeter_id"),
                    "perimeter_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "role_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "start_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                     description="Doit être dans le futur.\nSi vide ou null, sera défini à now().\nDoit contenir "
                                                                 "la timezone ou bien sera considéré comme UTC."),
                    "end_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                   description="Doit être dans le futur. \nSi vide ou null, sera défini à start_datetime +1 "
                                                               "an.\nDoit contenir la timezone ou bien sera considéré comme UTC.")},
        required=['profile', 'perimeter', 'role']))
    def create(self, request, *args, **kwargs):
        data = request.data
        if "care_site_id" not in data and 'perimeter_id' not in data:
            return Response(data="perimeter_id is required", status=status.HTTP_400_BAD_REQUEST)
        data['profile_id'] = data.get('profile_id', data.get('provider_history_id'))
        data['perimeter_id'] = data.get('perimeter_id', data.get('care_site_id'))
        response = super(AccessViewSet, self).create(request, *args, **kwargs)
        return response

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
        response = super(AccessViewSet, self).update(request, *args, **kwargs)
        return response

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_STRING, properties={}),
                         method="PATCH",
                         operation_summary="Will set end_datetime to now, to close the access.")
    @action(url_path="close", detail=True, methods=['patch'])
    def close(self, request, *args, **kwargs):
        access = self.get_object()
        now = timezone.now()
        if access.actual_end_datetime and access.actual_end_datetime < now:
            return Response(data="L'accès est déjà clôturé.", status=status.HTTP_403_FORBIDDEN)

        if access.actual_start_datetime and access.actual_start_datetime > now:
            return Response(data="L'accès n'a pas encore commencé, il ne peut pas être déjà fermé."
                                 "Il peut cependant être supprimé, avec la méthode DELETE.",
                            status=status.HTTP_403_FORBIDDEN)

        request.data.update({'end_datetime': now})
        response = self.partial_update(request, *args, **kwargs)

        user_accesses = get_user_valid_manual_accesses(user=access.profile.user)
        if not user_accesses:
            access.perimeter.remove_user_from_allowed_users(user_id=access.profile.user.provider_username)
        return response

    def destroy(self, request, *args, **kwargs):
        access = self.get_object()
        if access.actual_start_datetime:
            if access.actual_start_datetime < timezone.now():
                return Response(data="L'accès est déjà/a déjà été activé, il ne peut plus être supprimé.",
                                status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(access)
        response = Response(status=status.HTTP_204_NO_CONTENT)

        user_accesses = get_user_valid_manual_accesses(user=access.profile.user)
        if not user_accesses:
            access.perimeter.remove_user_from_allowed_users(user_id=access.profile.user.provider_username)
        return response

    @swagger_auto_schema(method='get',
                         operation_summary="Get the authenticated user's valid accesses.",
                         manual_parameters=[openapi.Parameter(name="expiring",
                                                              in_=openapi.IN_QUERY,
                                                              description="Filter accesses to expire soon",
                                                              type=openapi.TYPE_BOOLEAN)],
                         responses={200: openapi.Response('All valid accesses or ones to expire soon', AccessSerializer)})
    @action(url_path="my-accesses", methods=['get'], detail=False)
    @cache_response()
    def my_accesses(self, request, *args, **kwargs):
        user = request.user
        accesses = get_user_valid_manual_accesses(user=user)
        if request.query_params.get("expiring"):
            today = date.today()
            expiry_date = today + timedelta(days=ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS)
            to_expire_soon = Q(manual_end_datetime__date__gte=today) & Q(manual_end_datetime__date__lte=expiry_date)
            accesses_to_expire = accesses.filter(Q(profile__user=user) & to_expire_soon)

            if not accesses_to_expire:
                return Response(data={"message": f"No accesses to expire in the next {ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS} days"},
                                status=status.HTTP_200_OK)

            min_access_per_perimeter = {}
            for a in accesses_to_expire:
                if a.perimeter.id not in min_access_per_perimeter or \
                   a.manual_end_datetime < min_access_per_perimeter[a.perimeter.id].manual_end_datetime:
                    min_access_per_perimeter[a.perimeter.id] = a
                else:
                    continue
            accesses = min_access_per_perimeter.values()
        return Response(data=self.get_serializer(accesses, many=True).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_description="Returns particular type of objects, describing the data rights that a "
                                               "user has on a care-sites. AT LEAST one parameter is necessary",
                         manual_parameters=[i for i in map(lambda x: openapi.Parameter(
                             name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                             pattern=x[3] if len(x) == 4 else None),
                                                           [["care-site-ids", "(to deprecate -> perimeters_ids). care-sites list "
                                                                              "to limit the result on. Sep: ','", openapi.TYPE_STRING],
                                                            ["perimeters_ids", "Perimeters list to limit the result. Sep: ','", openapi.TYPE_STRING],
                                                            ["pop-children", "2deprecate(pop_children) If True, keeps "
                                                                             "only the biggest parents for each right", openapi.TYPE_BOOLEAN],
                                                            ["pop_children", "If True, keeps only the biggest parents for each right",
                                                             openapi.TYPE_BOOLEAN]])],
                         responses={200: openapi.Response('Rights found', DataRightSerializer),
                                    400: openapi.Response('perimeters_ids and pop_children are both null')})
    @action(url_path="my-rights", detail=False, methods=['get'], filter_backends=[], pagination_class=None)
    @cache_response()
    def my_rights(self, request, *args, **kwargs):
        perimeters_ids = request.query_params.get('perimeters_ids',
                                                  request.query_params.get('care-site-ids'))
        if perimeters_ids:
            urldecode_perimeters = urllib.parse.unquote(urllib.parse.unquote((str(perimeters_ids))))
            required_perimeters_ids = [int(i) for i in urldecode_perimeters.split(",")]
        else:
            required_perimeters_ids = []

        results = build_data_rights(user=request.user,
                                    expected_perim_ids=required_perimeters_ids,
                                    pop_children=False)
        return Response(data=DataRightSerializer(results, many=True).data,
                        status=status.HTTP_200_OK)

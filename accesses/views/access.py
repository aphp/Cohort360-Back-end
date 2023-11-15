from functools import reduce

from django.db.models import Q, BooleanField, When, Case, Value, QuerySet
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
from admin_cohort.views import BaseViewSet, CustomLoggingMixin
from accesses.models import Access, Perimeter, Role
from accesses.permissions import AccessesPermission
from accesses.serializers import AccessSerializer, DataRightSerializer, ExpiringAccessesSerializer
from accesses.tools import get_user_valid_manual_accesses, intersect_queryset_criteria, get_data_reading_rights, access_criteria_to_exclude, \
    user_is_full_admin, get_accesses_to_expire


class AccessFilter(filters.FilterSet):

    def perimeter_filter(self, queryset, field, value):
        perimeter = Perimeter.objects.get(pk=value)
        valid_accesses = queryset.filter(Access.q_is_valid())
        accesses_on_perimeter = valid_accesses.filter(perimeter_id=value)

        user_accesses = get_user_valid_manual_accesses(user=self.request.user)
        user_is_allowed_to_read_accesses_from_above_levels = user_accesses.filter(role__right_read_accesses_above_levels=True)\
                                                                          .exists()
        if user_is_allowed_to_read_accesses_from_above_levels:
            accesses_on_parent_perimeters = valid_accesses.filter(Q(perimeter_id__in=perimeter.above_levels)
                                                                  & Role.q_impact_inferior_levels())
            return accesses_on_perimeter.union(accesses_on_parent_perimeters)
        return accesses_on_perimeter

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
    perimeter = filters.CharFilter(method="perimeter_filter")

    ordering = OrderingFilter(fields=('start_datetime',
                                      'end_datetime',
                                      ('role__name', 'role_name'),
                                      ('sql_is_valid', 'is_valid')))

    class Meta:
        model = Access
        fields = "__all__"


class AccessViewSet(CustomLoggingMixin, BaseViewSet):
    serializer_class = AccessSerializer
    queryset = Access.objects.all()
    lookup_field = "id"
    filterset_class = AccessFilter
    permission_classes = [IsAuthenticated, AccessesPermission]
    http_method_names = ['get', 'post', 'patch', 'delete']
    logging_methods = ['POST', 'PATCH', 'DELETE']
    swagger_tags = ['Accesses - accesses']
    search_fields = ["profile__firstname",
                     "profile__lastname",
                     "profile__email",
                     "profile__user_id",
                     "perimeter__name"]

    def get_serializer_class(self):
        if self.request.method == "GET" and "expiring" in self.request.query_params:
            return ExpiringAccessesSerializer
        return self.serializer_class

    def get_queryset(self) -> QuerySet:
        queryset = super(AccessViewSet, self).get_queryset()
        user = self.request.user
        if not user.is_anonymous:
            accesses = get_user_valid_manual_accesses(user).select_related("role")
        else:
            accesses = []
        if user_is_full_admin(user):
            return queryset

        # todo: implement logic related to the recently added rights

        """
        the idea is, after having retrieved all the accesses queryset, some of them may get excluded
        according to what accesses the user X making the request is attributed.
        for example if the user X has an access with ONLY right_read_data_accesses_same_level on a perimeter P,
        then he cannot read the accesses configured on inferior levels of perimeter P.
        also, if he has an access with ONLY right_read_data_accesses_inferior_levels on a perimeter P,
        then he cannot read accesses configured on perimeter P
        """
        # todo: instead of using an exclude approach, proceed by filtering what accesses the user is allowed to retrieve
        to_exclude = [access_criteria_to_exclude(access) for access in accesses]
        if to_exclude:
            to_exclude = reduce(intersect_queryset_criteria, to_exclude)
            exclusion_queries = []
            for e in to_exclude:
                rights_sub_dict = {key: val for (key, val) in e.items() if 'perimeter' not in key}
                exclusion_query = Q(**{f'role__{right}': val for (right, val) in rights_sub_dict.items()})
                if e.get('perimeter_not'):
                    exclusion_query = exclusion_query \
                                      & ~Q(perimeter_id__in=e['perimeter_not'])
                if e.get('perimeter_not_child'):
                    exclusion_query = exclusion_query \
                                      & ~join_qs([Q(**{f"perimeter__{i * 'parent__'}id__in": e['perimeter_not_child']})
                                                  for i in range(1, len(PERIMETERS_TYPES))])
                exclusion_queries.append(exclusion_query)
            queryset = exclusion_queries and queryset.exclude(join_qs(exclusion_queries)) or queryset
        now = timezone.now()
        queryset = queryset.annotate(sql_is_valid=Case(When(start_datetime__lte=now, end_datetime__gte=now, then=Value(True)),
                                                       default=Value(False), output_field=BooleanField()))
        return queryset

    def get_object(self):                   # todo: why override it ?
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
        properties={"profile_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "perimeter_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "role_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "start_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                     description="Doit être dans le futur.\nSi vide ou null, sera défini à now().\nDoit contenir "
                                                                 "la timezone ou bien sera considéré comme UTC."),
                    "end_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                   description="Doit être dans le futur. \nSi vide ou null, sera défini à start_datetime +2 "
                                                               "ans.\nDoit contenir la timezone ou bien sera considéré comme UTC.")},
        required=['profile', 'perimeter', 'role']))
    def create(self, request, *args, **kwargs):
        return super(AccessViewSet, self).create(request, *args, **kwargs)

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

    @swagger_auto_schema(method="PATCH", operation_summary="Will set end_datetime to now, to close the access.")
    @action(url_path="close", detail=True, methods=['patch'])
    def close(self, request, *args, **kwargs):
        access = self.get_object()
        now = timezone.now()
        if access.end_datetime and access.end_datetime < now:
            return Response(data="L'accès est déjà clôturé.", status=status.HTTP_403_FORBIDDEN)
        if access.start_datetime and access.start_datetime > now:
            return Response(data="L'accès ne peut pas être clôturé car n'a pas encore commencé. Il peut cependant être supprimé.",
                            status=status.HTTP_403_FORBIDDEN)
        request.data.update({'end_datetime': now})
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        access = self.get_object()
        if access.start_datetime:
            if access.start_datetime < timezone.now():
                return Response(data="L'accès est déjà activé, il ne peut plus être supprimé.",
                                status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(access)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(operation_summary="Get the authenticated user's valid accesses.",
                         manual_parameters=[openapi.Parameter(name="expiring", description="Filter accesses to expire soon",
                                                              in_=openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN)],
                         responses={200: openapi.Response('All valid accesses or ones to expire soon', AccessSerializer)})
    @action(url_path="my-accesses", methods=['get'], detail=False, permission_classes=[IsAuthenticated])
    @cache_response()
    def get_my_accesses(self, request, *args, **kwargs):
        user = request.user
        accesses = get_user_valid_manual_accesses(user=user)
        if request.query_params.get("expiring"):
            accesses = get_accesses_to_expire(user=user, accesses=accesses)
            if not accesses:
                return Response(data={"message": f"No accesses to expire in the next {ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS} days"},
                                status=status.HTTP_200_OK)
        return Response(data=self.get_serializer(accesses, many=True).data,
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_description="Returns the list of rights allowing to read patients data on given perimeters.",
                         manual_parameters=[i for i in map(lambda x: openapi.Parameter(in_=openapi.IN_QUERY, name=x[0], description=x[1],
                                                                                       type=x[2], pattern=x[3] if len(x) == 4 else None),
                                                           [["perimeters_ids", "Perimeters IDs on which compute data rights, separated by ','",
                                                             openapi.TYPE_STRING]])],
                         responses={200: openapi.Response('Data Reading Rights computed per perimeter', DataRightSerializer)})
    @action(methods=['get'], url_path="my-data-rights", detail=False, permission_classes=[IsAuthenticated], pagination_class=None)
    @cache_response()
    def get_my_data_reading_rights(self, request, *args, **kwargs):
        perimeters_ids = request.query_params.get('perimeters_ids')
        data_rights = get_data_reading_rights(user=request.user, target_perimeters_ids=perimeters_ids)
        return Response(data=DataRightSerializer(data_rights, many=True).data,
                        status=status.HTTP_200_OK)

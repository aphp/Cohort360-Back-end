from typing import List, Tuple, Dict, OrderedDict

import django_filters
from django.db.models import Q, Prefetch, Value, BooleanField, When, Case
from django.db.models.functions import Coalesce
from django.utils import timezone

from django.http import Http404
from django_filters import OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AND
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN
import urllib

from .perimeters_API import ApiPerimeter
from .models import Role, Access, Profile, RoleType, \
    get_assignable_roles_on_perimeter, MANUAL_SOURCE, DataRight, \
    get_all_readable_accesses_perimeters, \
    get_user_dict_data_accesses, Q_readable_with_admin_mng, \
    Q_readable_with_data_admin, Q_readable_with_role_admin_access, \
    Q_readable_with_review_jup_mng_access, Q_readable_with_jupyter_mng_access, \
    Q_readable_with_csv_mng_access, Q_role_on_lower_levels, Perimeter, \
    get_all_level_parents_perimeters, Q_readable_with_review_csv_mng_access, \
    get_user_valid_manual_accesses_queryset
from .permissions import RolePermissions, AccessPermissions, \
    can_user_manage_review_transfer_jupyter_accesses, \
    can_user_manage_transfer_jupyter_accesses, \
    can_user_manage_review_export_csv_accesses, \
    can_user_manage_export_csv_accesses, ProfilePermissions, \
    HasUserAddingPermission
from .serializers import RoleSerializer, AccessSerializer, \
    ProfileSerializer, ReducedProfileSerializer, \
    ProfileCheckSerializer, DataRightSerializer, PerimeterSerializer, \
    TreefiedPerimeterSerializer
from admin_cohort import conf_auth
from admin_cohort.permissions import IsAuthenticated, can_user_edit_roles, \
    IsAuthenticatedReadOnly, OR, can_user_read_users
from admin_cohort.settings import ROOT_PERIMETER_TYPE, PERIMETERS_TYPES
from admin_cohort.tools import join_qs
from admin_cohort.views import BaseViewset, CustomLoggingMixin, \
    YarnReadOnlyViewsetMixin
from admin_cohort.models import User


class ProfileFilter(django_filters.FilterSet):
    provider_source_value = django_filters.CharFilter(field_name="user")
    provider_name = django_filters.CharFilter(lookup_expr="icontains")
    lastname = django_filters.CharFilter(lookup_expr="icontains")
    firstname = django_filters.CharFilter(lookup_expr="icontains")
    email = django_filters.CharFilter(lookup_expr="icontains")

    provider_history_id = django_filters.NumberFilter(field_name='id')

    cdm_source = django_filters.CharFilter(field_name='source')

    class Meta:
        model = Profile
        fields = (
            "provider_id",
            "source", "cdm_source",
            "user", "provider_source_value",
            "provider_name",
            "lastname",
            "firstname",
            "email",
            "provider_history_id", "id",
            "is_active"
        )


class ProfileViewSet(CustomLoggingMixin, BaseViewset):
    queryset = Profile.objects.filter(delete_datetime__isnull=True).all()
    lookup_field = "id"
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']

    user_fields = [f.column for f in User._meta.local_fields]
    ph_fields = [f.column for f in Profile._meta.local_fields]
    permission_classes = [
        lambda: AND(IsAuthenticated(), ProfilePermissions()),
    ]
    filter_class = ProfileFilter
    search_fields = ["lastname", "firstname", "email", "user_id"]

    # search_fields = [
    #     "p.provider_name", "p.lastname", "p.firstname", "p.email", "p.user_id"]

    def get_serializer_context(self):
        return {'request': self.request}

    def get_serializer_class(self):
        return (ReducedProfileSerializer
                if self.request.method == 'GET'
                and not can_user_read_users(self.request.user)
                else ProfileSerializer)

    def get_list_queryset(self):
        return super(ProfileViewSet, self).get_list_queryset()\
            .select_related('user')

    @swagger_auto_schema(
        manual_parameters=list(map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None),
            [
                ["provider_source_value",
                 "(to deprecate -> user) Search type",
                 openapi.TYPE_STRING, r"\d{1,7}"],
                ["user", "Filter type (User's id)", openapi.TYPE_STRING,
                 r"\d{1,7}"],
                ["provider_name", "Search type", openapi.TYPE_STRING],
                ["email", "Search type", openapi.TYPE_STRING],
                ["lastname", "Search type", openapi.TYPE_STRING],
                ["firstname", "Search type", openapi.TYPE_STRING],
                ["provider_history_id", "(to deprecate -> id) Filter type",
                 openapi.TYPE_INTEGER],
                ["id", "Filter type", openapi.TYPE_INTEGER],
                ["provider_id", "Filter type", openapi.TYPE_INTEGER],
                ["cdm_source",
                 "(to deprecate -> source) Filter type "
                 "('MANUAL', 'ORBIS', etc.)",
                 openapi.TYPE_STRING],
                ["source", "Filter type ('MANUAL', 'ORBIS', etc.)",
                 openapi.TYPE_STRING],
                ["is_active", "Filter type", openapi.TYPE_BOOLEAN],
                [
                    "search",
                    "Filter on several fields (provider_source_value, "
                    "provider_name, lastname, firstname, email)",
                    openapi.TYPE_STRING
                ],
            ])))
    def list(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "firstname": openapi.Schema(type=openapi.TYPE_STRING),
            "lastname": openapi.Schema(type=openapi.TYPE_STRING),
            "email": openapi.Schema(type=openapi.TYPE_STRING),
            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        }))
    def partial_update(self, request, *args, **kwargs):
        return super(ProfileViewSet, self)\
            .partial_update(request, *args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def update(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).update(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "firstname": openapi.Schema(type=openapi.TYPE_STRING),
            "lastname": openapi.Schema(type=openapi.TYPE_STRING),
            "email": openapi.Schema(type=openapi.TYPE_STRING),
            "provider_id": openapi.Schema(type=openapi.TYPE_INTEGER,
                                          description="(to deprecate)"),
            "user": openapi.Schema(type=openapi.TYPE_STRING),
            "provider_source_value": openapi.Schema(
                type=openapi.TYPE_STRING, description="(to deprecate)"),
        }))
    def create(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.entry_deleted_by = self.request.user.provider_username
        return super(ProfileViewSet, self).perform_destroy(instance)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "provider_source_value": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="(to deprecate, user 'user_id' instead)"),
            "user_id": openapi.Schema(type=openapi.TYPE_STRING),
        }
    ), responses={
        '201': openapi.Response("User found", ProfileCheckSerializer()),
        '204': openapi.Response("No user found")
    })
    @action(
        detail=False, methods=['post'],
        permission_classes=(HasUserAddingPermission,), url_path="check"
    )
    def check_existing_user(self, request, *args, **kwargs):
        from admin_cohort.serializers import UserSerializer

        psv = self.request.data.get(
            "user_id", self.request.data.get("provider_source_value", None))
        if not psv:
            return Response("No provider_source_value provided",
                            status=status.HTTP_400_BAD_REQUEST)
        person = conf_auth.check_id_aph(psv)
        if person is not None:
            manual_profile: Profile = Profile.objects.filter(
                Profile.Q_is_valid()
                & Q(user=person)
                & Q(source=MANUAL_SOURCE)
            ).first()

            user: User = User.objects.filter(
                provider_username=person.user_id,
            ).first()
            u_data = UserSerializer(user).data if user else None

            data = ProfileCheckSerializer({
                "firstname": person.firstname,
                "lastname": person.lastname,
                "user_id": person.user_id,
                "email": person.email,
                "provider":  u_data,
                "user":  u_data,
                "manual_profile": manual_profile
            }).data
            return Response(
                data, status=status.HTTP_200_OK,
                headers=self.get_success_headers(data)
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Role
        fields = "__all__"


class RoleViewSet(CustomLoggingMixin, BaseViewset):
    serializer_class = RoleSerializer
    queryset = Role.objects.filter(delete_datetime__isnull=True).all()
    lookup_field = "id"
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    filter_class = RoleFilter

    def get_permissions(self):
        return [AND(IsAuthenticated(), RolePermissions())]

    @swagger_auto_schema(
        method='get',
        operation_summary="Get roles that the user can assign to a user on "
                          "the perimeter provided.",
        manual_parameters=[
            openapi.Parameter(
                name="care_site_id", in_=openapi.IN_QUERY,
                description="(to deprecate -> perimeter_id) Required",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                name="perimeter_id", in_=openapi.IN_QUERY,
                description="Required", type=openapi.TYPE_INTEGER
            )
        ]
    )
    @action(
        detail=False, methods=['get'], permission_classes=(IsAuthenticated,),
        url_path="assignable"
    )
    def assignable(self, request, *args, **kwargs):
        perim_id = self.request.GET.get(
            "perimeter_id", self.request.GET.get("care_site_id", None))
        if perim_id is None:
            raise ValidationError("Missing parameter 'perimeter_id'")
        roles = get_assignable_roles_on_perimeter(self.request.user, perim_id)
        q = Role.objects.filter(id__in=[r.id for r in roles])
        page = self.paginate_queryset(q)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(q, many=True)
        return Response(serializer.data)


def build_data_rights(user_id: str, provider_id: int,
                      required_cs_ids: List[str],
                      data_accesses: Dict[int, Access],
                      pop_previous_rights: bool = False) -> List[DataRight]:
    # we build a rootified (opposite of treefied, list of perimeters whom
    # we plug the parent to) version of the tree structure of the care-sites
    # with the cs_ids previously defined as the roots
    parents = get_all_level_parents_perimeters(required_cs_ids)
    if not len(parents):
        raise ValidationError("Aucun périmètre correspondant trouvé")
    serializer = PerimeterSerializer(parents, many=True)
    rootified = rootify_perimeters(serializer.data, required_cs_ids)

    results = get_data_rights_on_roots(
        rootified, user_id, provider_id,
        required_cs_ids, data_accesses,
        pop_previous_rights)

    # add export rights
    nomi_exports_acc_ids = [a.id for a in data_accesses.values()
                            if a.role.right_export_csv_nominative]
    pseudo_exports_acc_ids = [a.id for a in data_accesses.values()
                              if a.role.right_export_csv_pseudo_anonymised]
    # add jupyter transfert rights
    nomi_jupy_acc_ids = [a.id for a in data_accesses.values()
                         if a.role.right_transfer_jupyter_nominative]
    pseudo_jupy_acc_ids = [a.id for a in data_accesses.values()
                           if a.role.right_transfer_jupyter_pseudo_anonymised]

    for r in results:
        r.add_access_ids(nomi_exports_acc_ids + pseudo_exports_acc_ids)
        r.right_export_csv_nominative = len(nomi_exports_acc_ids) > 0
        r.right_export_csv_pseudo_anonymised = \
            len(pseudo_exports_acc_ids) > 0

        r.add_access_ids(nomi_jupy_acc_ids + pseudo_jupy_acc_ids)
        r.right_transfer_jupyter_nominative = len(nomi_jupy_acc_ids) > 0
        r.right_transfer_jupyter_pseudo_anonymised = \
            len(pseudo_jupy_acc_ids) > 0

    return results


class AccessFilter(django_filters.FilterSet):
    def target_perimeter_filter(self, queryset, field, value):
        if value:
            parents = get_all_level_parents_perimeters([value], ids_only=True)

            return queryset.filter(Q(perimeter_id=value)
                                   | (Q(perimeter_id__in=parents)
                                      & Q_role_on_lower_levels('role')))

        return queryset

    # def perimeter_id_filter(self, queryset, field, value):
    #     if not len(value):
    #         return queryset
    #     filtered_perim_ids = conf.get_perimeters_ids(ids=value.split(","))
    #     return queryset.filter(perimeter_id__in=filtered_perim_ids)

    provider_email = django_filters.CharFilter(
        lookup_expr="icontains", field_name="profile__email")
    provider_lastname = django_filters.CharFilter(
        lookup_expr="icontains", field_name="profile__lastname")
    provider_firstname = django_filters.CharFilter(
        lookup_expr="icontains", field_name="profile__firstname")
    provider_source_value = django_filters.CharFilter(
        lookup_expr="icontains", field_name="profile__user_id")
    provider_id = django_filters.CharFilter(field_name="profile__provider_id")
    provider_history_id = django_filters.CharFilter(field_name="profile_id")

    profile_email = django_filters.CharFilter(
        lookup_expr="icontains", field_name="profile__email")
    profile_lastname = django_filters.CharFilter(
        lookup_expr="icontains", field_name="profile__lastname")
    profile_firstname = django_filters.CharFilter(
        lookup_expr="icontains", field_name="profile__firstname")
    profile_user_id = django_filters.CharFilter(
        lookup_expr="icontains", field_name="profile__user__pk")
    profile_id = django_filters.CharFilter(field_name="profile_id")

    perimeter_name = django_filters.CharFilter(field_name="perimeter__name",
                                               lookup_expr="icontains")
    care_site_id = django_filters.CharFilter(field_name="perimeter_id")
    # perimeter_id = django_filters.CharFilter(
    #     method="perimeter_id_filter")

    target_care_site_id = django_filters.CharFilter(
        method="target_perimeter_filter")
    target_perimeter_id = django_filters.CharFilter(
        method="target_perimeter_filter")

    ordering = OrderingFilter(
        fields=(
            ('role__name', 'role_name'),
            ('sql_actual_start_datetime', 'start_datetime'),
            ('sql_actual_end_datetime', 'end_datetime'),
            ('sql_is_valid', 'is_valid'),
        )
    )

    class Meta:
        model = Access
        fields = (
            "profile_email", "provider_email",
            "profile_lastname", "provider_lastname",
            "profile_firstname", "provider_firstname",
            "profile_user_id", "provider_source_value",
            "provider_id",
            "profile_id", "provider_history_id",
            "perimeter", "care_site_id",
            "target_perimeter_id", "target_care_site_id",
        )


class AccessViewSet(CustomLoggingMixin, BaseViewset):
    serializer_class = AccessSerializer
    queryset = Access.objects.all()
    lookup_field = "id"
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']

    search_fields = [
        "profile__lastname",
        "profile__firstname",
        "perimeter__name",
        "profile__email",
        "profile__user__provider_username"
    ]
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,
                       filters.SearchFilter)
    filter_class = AccessFilter

    def get_serializer_context(self):
        return {'request': self.request}

    def get_permissions(self):
        if self.action in ['my_accesses', 'data_rights']:
            return [IsAuthenticated()]
        return [AND(IsAuthenticated(), AccessPermissions())]

    def get_queryset(self) -> Tuple[any, Dict[str, ApiPerimeter]]:
        q = super(AccessViewSet, self).get_queryset()

        user = self.request.user
        accesses = self.request.user.valid_accesses

        admin_perimeters_ids = get_all_readable_accesses_perimeters(
            accesses=accesses,
            role_type=RoleType.ADMIN_MANAGER_READ,
        )
        data_perimeters_ids = get_all_readable_accesses_perimeters(
            accesses=accesses,
            role_type=RoleType.ADMIN_READ,
        )

        is_main_admin = can_user_edit_roles(user=user)

        can_read_review_transfer_jupyter_accesses = \
            can_user_manage_review_transfer_jupyter_accesses(user=user)
        can_read_transfer_jupyter_accesses = \
            can_user_manage_transfer_jupyter_accesses(user=user)
        can_read_review_export_csv_accesses = \
            can_user_manage_review_export_csv_accesses(user=user)
        can_read_export_csv_accesses = can_user_manage_export_csv_accesses(
            user=user
        )

        if not any([
            is_main_admin, len(admin_perimeters_ids), len(data_perimeters_ids),
            can_read_review_transfer_jupyter_accesses,
            can_read_transfer_jupyter_accesses,
            can_read_review_export_csv_accesses,
            can_read_export_csv_accesses,
        ]):
            raise PermissionDenied(
                "Aucun droit de lecture sur accès trouvé"
            )

        role_type_qs = []
        if len(admin_perimeters_ids):
            role_type_qs.append(
                Q(perimeter_id__in=admin_perimeters_ids)
                & Q_readable_with_admin_mng('role'))

        if len(data_perimeters_ids):
            role_type_qs.append(
                Q(perimeter_id__in=data_perimeters_ids)
                & Q_readable_with_data_admin('role'))

        if is_main_admin:
            role_type_qs.append(Q_readable_with_role_admin_access('role'))

        if can_read_review_transfer_jupyter_accesses:
            role_type_qs.append(Q_readable_with_review_jup_mng_access('role'))

        if can_read_transfer_jupyter_accesses:
            role_type_qs.append(Q_readable_with_jupyter_mng_access('role'))

        if can_read_review_export_csv_accesses:
            role_type_qs.append(Q_readable_with_review_csv_mng_access('role'))

        if can_read_export_csv_accesses:
            role_type_qs.append(Q_readable_with_csv_mng_access('role'))

        if len(role_type_qs):
            q = q.filter(join_qs(role_type_qs))

        q = q.select_related('profile', 'role')

        return q

    def filter_queryset(self, queryset):
        now = timezone.now()
        queryset = queryset.annotate(
            sql_start_datetime=Coalesce('manual_start_datetime',
                                        'start_datetime'),
            sql_end_datetime=Coalesce('manual_end_datetime', 'end_datetime')
        ).annotate(
            sql_is_valid=Case(
                When(sql_start_datetime__lte=now,
                     sql_end_datetime__gte=now, then=Value(True)),
                default=Value(False), output_field=BooleanField()
            )
        )
        return super(AccessViewSet, self).filter_queryset(queryset)

    @swagger_auto_schema(
        manual_parameters=list(map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None
            ), [
                ["perimeter_id", "Filter type", openapi.TYPE_STRING],
                ["target_perimeter_id",
                 "Filter type. Used to also get accesses "
                 "on parents of this perimeter", openapi.TYPE_STRING],
                ["profile_email", "Search type", openapi.TYPE_STRING],
                ["profile_name", "Search type", openapi.TYPE_STRING],
                ["profile_lastname", "Search type", openapi.TYPE_STRING],
                ["profile_firstname", "Search type", openapi.TYPE_STRING],
                ["profile_user_id", "Search type", openapi.TYPE_STRING,
                 r'\d{1,7}'],
                ["profile_id", "Filter type", openapi.TYPE_STRING],
                [
                    "search",
                    "Will search in multiple fields (perimeter_name, "
                    "provider_name, lastname, firstname, "
                    "provider_source_value, email)", openapi.TYPE_STRING
                ],
                [
                    "ordering",
                    "To sort the result. Can be care_site_name, role_name, "
                    "start_datetime, end_datetime, is_valid. Use -field for "
                    "descending order", openapi.TYPE_STRING
                ],
            ])))
    def list(self, request, *args, **kwargs):
        return super(AccessViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "provider_history_id": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="(to deprecate -> profile_id) "
                            "Correspond à Provider_history_id"
            ),
            "profile_id": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="Correspond à un id de Profile"
            ),
            "care_site_id": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="(to deprecate -> perimeter_id"),
            "perimeter_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            "role_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            "start_datetime": openapi.Schema(
                type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                description="Doit être dans le futur. "
                            "\nSi vide ou null, sera défini à now(). "
                            "\nDoit contenir la timezone ou bien sera "
                            "considéré comme UTC."
            ),
            "end_datetime": openapi.Schema(
                type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                description="Doit être dans le futur. \nSi vide ou null, "
                            "sera défini à start_datetime + 1 un an. "
                            "\nDoit contenir la timezone ou bien sera"
                            " considéré comme UTC."
            ),
        }, required=['profile', 'perimeter', 'role']))
    def create(self, request, *args, **kwargs):
        if "care_site_id" not in request.data \
                and 'perimeter_id' not in request.data:
            return Response({"response": "perimeter_id is required"},
                            status=status.HTTP_404_NOT_FOUND)
        request.data['profile_id'] = request.data.get(
            'profile_id', request.data.get('provider_history_id'))
        request.data['perimeter_id'] = request.data.get(
            'perimeter_id', request.data.get('care_site_id'))
        return super(AccessViewSet, self).create(
            request, *args, **kwargs
        )

    def dispatch(self, request, *args, **kwargs):
        return super(AccessViewSet, self).dispatch(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "start_datetime": openapi.Schema(
                type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                description="Doit être dans le futur. \nNe peut pas être "
                            "modifié si start_datetime actuel est déja passé. "
                            "\nSera mis à now() si null. \nDoit contenir la "
                            "timezone ou bien sera considéré comme UTC."
            ),
            "end_datetime": openapi.Schema(
                type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                description="Doit être dans le futur. \nNe peut pas être "
                            "modifié si end_datetime actuel est déja passé.\n"
                            "Ne peut pas être mise à null. \nDoit contenir la "
                            "timezone ou bien sera considéré comme UTC."
            ),
        }))
    def partial_update(self, request, *args, **kwargs):
        return super(AccessViewSet, self).partial_update(
            request, *args, **kwargs
        )

    @swagger_auto_schema(auto_schema=None)
    def update(self, request, *args, **kwargs):
        return super(AccessViewSet, self).update(
            request, *args, **kwargs
        )

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_STRING,
            properties={}
        ),
        method="PATCH",
        operation_summary="Will set end_datetime to now, to close the access."
    )
    @action(detail=True, methods=['patch'],
            permission_classes=(IsAuthenticated,), url_path="close")
    def close(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.actual_end_datetime is not None:
            end_datetime = timezone.get_current_timezone().localize(
                instance.actual_end_datetime
            ) if getattr(instance.actual_end_datetime, "tzinfo", None) is None \
                else instance.actual_end_datetime

            if end_datetime < timezone.now():
                return Response(
                    "L'accès est déjà terminé, "
                    "il ne peut pas être à nouveau fermé.",
                    status.HTTP_403_FORBIDDEN
                )

        if instance.actual_start_datetime is not None:
            start_datetime = timezone.get_current_timezone().localize(
                instance.actual_start_datetime
            ) if getattr(instance.actual_start_datetime, "tzinfo", None) \
                 is None else instance.actual_start_datetime

            if start_datetime > timezone.now():
                return Response(
                    "L'accès n'a pas encore commencé, "
                    "il ne peut pas être déjà fermé. "
                    "Il peut cependant être supprimé, avec la méthode DELETE.",
                    status.HTTP_403_FORBIDDEN
                )

        request.data.update({'end_datetime': timezone.now()})
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.actual_start_datetime is not None:
            start_datetime = timezone.get_current_timezone().localize(
                instance.actual_start_datetime
            ) if getattr(instance.actual_start_datetime, "tzinfo", None) \
                 is None else instance.actual_start_datetime

            if start_datetime < timezone.now():
                return Response(
                    "L'accès est déjà/a déjà été actif, "
                    "il ne peut plus être supprimé.",
                    status.HTTP_403_FORBIDDEN
                )
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

    @swagger_auto_schema(
        method='get',
        operation_summary="Get the authenticated user's valid accesses."
    )
    @action(detail=False, methods=['get'], url_path="my-accesses")
    def my_accesses(self, request, *args, **kwargs):
        q = get_user_valid_manual_accesses_queryset(self.request.user)
        serializer = self.get_serializer(q, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Returns particular type of objects, describing "
                              "the data rights that a user has on a care-sites."
                              " AT LEAST one parameter is necessary",
        manual_parameters=[i for i in map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None
            ), [
                [
                    "care-site-ids",
                    "(to deprecate -> perimeters_ids) "
                    "List of care-sites to limit the result on. Sep: ','",
                    openapi.TYPE_STRING
                ],
                [
                    "perimeters_ids",
                    "List of perimeters to limit the result on. Sep: ','",
                    openapi.TYPE_STRING
                ],
                [
                    "pop-children",
                    "(to deprecate -> pop_children) If True, keeps only the "
                    "biggest parents for each right",
                    openapi.TYPE_BOOLEAN
                ],
                [
                    "pop_children",
                    "If True, keeps only the biggest parents for each right",
                    openapi.TYPE_BOOLEAN
                ]
                ])],
        responses={200: openapi.Response('Rights found', DataRightSerializer),
                   403: openapi.Response('perimeters_ids and '
                                         'pop_children are both null')}
    )
    @action(detail=False, methods=['get'], url_path="my-rights",
            filter_backends=[], pagination_class=None)
    def data_rights(self, request, *args, **kwargs):
        param_perimeters = self.request.GET.get(
            'perimeters_ids', self.request.GET.get('care-site-ids', None))
        pop_previous_rights = self.request.GET.get(
            'pop_children', self.request.GET.get('pop-children', None))
        if param_perimeters is None and pop_previous_rights is None:
            return Response("Cannot have both 'perimeters-ids/care-site-ids' "
                            "and 'pop-children' at null (would return rights on"
                            " all Perimeters).", status=HTTP_403_FORBIDDEN)

        user = self.request.user
        data_accesses = get_user_dict_data_accesses(user)

        # if the result is asked only for a list of perimeters,
        # we start our search on these
        if param_perimeters:
            urldecode_perimeters = urllib.parse.unquote(
                urllib.parse.unquote((str(param_perimeters))))
            required_cs_ids: List[int] = [int(i) for i in
                                          urldecode_perimeters.split(",")]
        # else, we start our search on the accesses we found
        else:
            required_cs_ids: List[int] = [a.perimeter.id
                                          for a in data_accesses.values()]

        results = build_data_rights(
            user.provider_username, self.request.user.provider_id,
            required_cs_ids, data_accesses, pop_previous_rights)

        return Response(data=DataRightSerializer(results, many=True).data,
                        status=status.HTTP_200_OK)


# todo : set required_perim_ids type as List[str]
#  and also better type for perimeter_roots
def get_data_rights_on_roots(
        perimeter_roots: List[OrderedDict], user_id: str,
        provider_id: int,
        required_perim_ids: List[str],
        data_accesses: Dict[int, Access],
        pop_previous_rights: bool = False
) -> List[DataRight]:
    results: Dict[str, DataRight] = dict()

    for p in perimeter_roots:
        curr_p = p
        impacted = []
        should_end = False
        while curr_p and not should_end:
            curr_p_id = curr_p['id']

            if curr_p_id in results:
                curr_right: DataRight = results[curr_p_id]
                # if id is already in presents,
                # the rest of the root was already explored
                should_end = True
            else:
                curr_right = DataRight(curr_p_id, user_id, provider_id)
                if curr_p_id in required_perim_ids:
                    results[curr_p_id] = curr_right

                matching_accesses = [a for a in data_accesses.values()
                                     if a.perimeter.id == curr_p_id]
                if len(matching_accesses) > 0:
                    curr_right.add_right(
                        DataRight(
                            p_id=curr_p_id,
                            user_id=user_id,
                            provider_id=provider_id,
                            acc_ids=[a.id for a in matching_accesses],
                            pseudo=any([
                                a.role.right_read_patient_pseudo_anonymised
                                for a in matching_accesses]),
                            nomi=any([
                                a.role.right_read_patient_nominative for a
                                in matching_accesses]),
                            search_ipp=any([
                                a.role.right_search_patient_with_ipp for a
                                in matching_accesses]),
                        ))

            # pop_previous_rights means the result should show only
            # the top accesses, without showing smaller, redundant accesses
            if pop_previous_rights:
                # we remove any previous result if the new access,
                # further in the branch, is stronger
                popped = []
                for previous_right in impacted:
                    previous_id = previous_right.perimeter_id
                    if (
                            curr_right.right_read_patient_nominative
                            and previous_right.right_read_patient_nominative
                    ) or (
                            curr_right.right_read_patient_pseudo_anonymised
                            and
                            previous_right.right_read_patient_pseudo_anonymised
                    ) or (
                            curr_right.right_search_patient_with_ipp
                            and
                            previous_right.right_search_patient_with_ipp
                    ):
                        results.pop(previous_id)
                        popped.append(previous_id)
                impacted = [dr for dr in impacted if
                            dr.perimeter_id not in popped]
            else:
                # we complete any previous result with the new access
                if curr_right.has_data_read_right:
                    for i in impacted:
                        i.add_right(curr_right)

            impacted.append(curr_right)
            curr_p = curr_p['parent'] if 'parent' in curr_p else None

    return list(results.values())


def rootify_perimeters(
        perimeters: List[OrderedDict], roots_ids: List[str]
) -> List[OrderedDict]:
    """
    Given a full list of Perimeters that contain 'parent_id' that will
    necessary be within the list,
    returns the small list of perimeters from the roots_ids, completed
    with the field parent showing directly the matching perimeter
    @param perimeters: full list of perimeters
    @param roots_ids: ids of the perimeters that should be returned
    @return:
    """
    dct = dict([(str(cs["id"]), cs) for cs in perimeters])
    roots = [dct[str(id)] for id in roots_ids if str(id) in dct]

    for cs in roots:
        curr_cs = cs
        while curr_cs["type_source_value"] != ROOT_PERIMETER_TYPE \
                and "parent" not in curr_cs:
            parent_id = curr_cs["parent_id"]
            parent = dct[parent_id]
            curr_cs["parent"] = parent
            curr_cs = parent

    return roots


class PerimeterFilter(django_filters.FilterSet):
    care_site_name = django_filters.CharFilter(field_name='name')
    care_site_type_source_value = django_filters.CharFilter(
        field_name='type_source_value')
    care_site_source_value = django_filters.CharFilter(
        field_name='source_value')
    care_site_id = django_filters.CharFilter(field_name='id')
    name = django_filters.CharFilter(lookup_expr='icontains')
    source_value = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Perimeter
        fields = (
            "care_site_name",
            "care_site_type_source_value",
            "care_site_source_value",
            "care_site_id",
            "name",
            "type_source_value",
            "source_value",
            "id",
        )


class PerimeterViewSet(YarnReadOnlyViewsetMixin, BaseViewset):
    serializer_class = PerimeterSerializer
    lookup_field = "id"

    filterset_class = PerimeterFilter
    ordering_fields = [('care_site_name', 'name'),
                       ('care_site_type_source_value', 'type_source_value'),
                       ('care_site_source_value', 'source_value')]
    search_fields = [
        "name", "type_source_value",
        "source_value"
    ]

    def get_queryset(self):
        return Perimeter.objects.all()

    def get_permissions(self):
        return OR(IsAuthenticatedReadOnly(),)

    @swagger_auto_schema(
        method='get',
        operation_summary="Get the care_sites on which the user has at least "
                          "one role that allows to give accesses.",
        manual_parameters=list(map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None
            ), [
                [
                    "search",
                    "Will search in multiple fields (care_site_name, "
                    "care_site_type_source_value, care_site_source_value)",
                    openapi.TYPE_STRING
                ],
                [
                    "nb_levels",
                    "Indicates the limit of children layers to reply.",
                    openapi.TYPE_INTEGER
                ],
            ]
        ))
    )
    @action(detail=False, methods=['get'], url_path="manageable")
    def get_manageable(self, request, *args, **kwargs):
        from accesses.models import RoleType,  \
            get_all_readable_accesses_perimeters
        user_accesses = get_user_valid_manual_accesses_queryset(
            self.request.user)

        perim_ids = get_all_readable_accesses_perimeters(
                user_accesses,
                role_type=RoleType.MANAGING_ACCESS
            )

        max_levels = len(PERIMETERS_TYPES)
        nb_levels = int(request.GET.get('nb_levels', max_levels))
        better_q = Perimeter.objects.filter(
            (
                ~Q(parent__id__in=perim_ids)
            )
            & Q(id__in=perim_ids)
        )

        prefetch = Prefetch(
            'children', queryset=Perimeter.objects.filter(id__in=perim_ids),
            to_attr='prefetched_children')
        for _ in range(2, nb_levels):
            prefetch = Prefetch(
                'children',
                queryset=(Perimeter.objects.filter(id__in=perim_ids)
                          .prefetch_related(prefetch)),
                to_attr='prefetched_children')
        better_q = better_q.prefetch_related(prefetch)

        better_treefied = TreefiedPerimeterSerializer(better_q, many=True).data

        return Response(better_treefied)

    @action(detail=True, methods=['get'], url_path="children")
    def children(self, request, *args, **kwargs):
        cs = self.get_object()
        q = cs.children.all()

        page = self.paginate_queryset(q)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(q, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        manual_parameters=list(map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None
            ), [
                [
                    "ordering",
                    "'field' or '-field' in care_site_name, "
                    "care_site_type_source_value, care_site_source_value, ",
                    openapi.TYPE_STRING
                ],
                [
                    "search",
                    "Will search in multiple fields (care_site_name, "
                    "care_site_type_source_value, care_site_source_value)",
                    openapi.TYPE_STRING
                ],
                [
                    "treefy",
                    "If true, returns a tree-organised json, else, "
                    "returns a list", openapi.TYPE_BOOLEAN
                ],
                ])))
    def list(self, request, *args, **kwargs):
        q = self.filter_queryset(self.get_queryset())

        treefy = request.GET.get("treefy", None)
        if str(treefy).lower() == 'true':
            if not len(q):
                return Response([])

            filtered_ids = q.values_list("id", flat=True)
            full_root = Perimeter.objects.filter(join_qs([
                Q(**{i * 'children__' + 'id__in': filtered_ids})
                for i in range(0, len(PERIMETERS_TYPES))
            ])).distinct()
            full_root_ids = full_root.values_list("id", flat=True)

            res = full_root.filter(~Q(parent__id__in=full_root_ids))

            prefetch = Prefetch(
                'children',
                queryset=Perimeter.objects.filter(id__in=full_root_ids),
                to_attr='prefetched_children'
            )
            for _ in range(2, len(PERIMETERS_TYPES)):
                prefetch = Prefetch(
                    'children',
                    queryset=(Perimeter.objects.filter(id__in=full_root_ids)
                              .prefetch_related(prefetch)),
                    to_attr='prefetched_children'
                )
            res = res.prefetch_related(prefetch)
            better_treefied = TreefiedPerimeterSerializer(res, many=True).data

            return Response(better_treefied)
        else:
            page = self.paginate_queryset(q)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                data = serializer.data
                return self.get_paginated_response(data)

        serializer = self.get_serializer(q, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return super(PerimeterViewSet, self).retrieve(request, *args, **kwargs)

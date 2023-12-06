import logging
import re
from datetime import timedelta

from django.db.models import Max, Q
from django.utils import timezone
from django.utils.datetime_safe import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from admin_cohort.models import User
from admin_cohort.serializers import BaseSerializer, ReducedUserSerializer, UserSerializer
from admin_cohort.settings import MANUAL_SOURCE, MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS
from .conf_perimeters import Provider
from .models import Role, Access, Profile, Perimeter
from .services.profiles import profiles_service
from .services.roles import roles_service

_logger = logging.getLogger('django.request')


def check_date_rules(new_start_datetime: datetime = None, new_end_datetime: datetime = None,
                     old_start_datetime: datetime = None, old_end_datetime: datetime = None):
    try:
        old_start_datetime = old_start_datetime and timezone.get_current_timezone().localize(old_start_datetime)
        old_end_datetime = old_end_datetime and timezone.get_current_timezone().localize(old_end_datetime)
    except ValueError:
        pass
    now = timezone.now()

    if old_start_datetime and new_start_datetime \
       and old_start_datetime != new_start_datetime \
       and old_start_datetime < now:
        raise ValidationError(f"La date de début {old_start_datetime} ne peut pas être modifiée si elle est passée")

    if old_end_datetime and new_end_datetime \
       and old_end_datetime != new_end_datetime \
       and old_end_datetime < now:
        raise ValidationError(f"La date de fin {old_end_datetime} ne peut pas être modifiée si elle est passée")

    if new_start_datetime and new_start_datetime + timedelta(seconds=10) < now:
        raise ValidationError(f"La date de début {new_start_datetime} ne peut pas être dans le passé")

    if new_end_datetime and new_end_datetime + timedelta(seconds=10) < now:
        raise ValidationError(f"La date de fin {new_end_datetime} ne peut pas être dans le passé")

    if new_start_datetime and new_end_datetime and new_end_datetime < new_start_datetime:
        raise ValidationError(f"La date de fin {new_end_datetime} ne peut pas précéder la date de début {new_start_datetime}")


def fix_access_dates(validated_data, for_update: bool = False):
    start_datetime = validated_data.pop("start_datetime", 0)
    end_datetime = validated_data.pop("end_datetime", 0)

    start_is_empty = start_datetime == 0
    end_is_empty = end_datetime == 0

    # if creating an access, then start_datetime will be now() if empty or null
    if not for_update:
        validated_data["start_datetime"] = start_datetime \
            if start_datetime is not None and not start_is_empty \
            else timezone.now()
    # if updating a csh, then start_date will be now() if null
    elif not start_is_empty:
        validated_data["start_datetime"] = start_datetime \
            if start_datetime is not None \
            else timezone.now()

    # we deny it if is for updating, and end_datetime has been set to null
    if not end_is_empty and end_datetime is None and for_update:
        raise ValidationError("You cannot set end_datetime "
                              "at null when updating")

    # if there is no value, and it is not for updating, we set end_datetime
    if end_datetime != 0 or not for_update:
        validated_data["end_datetime"] = end_datetime \
            if end_datetime is not None and not end_is_empty \
            else validated_data["start_datetime"] + timedelta(days=MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS)

    return validated_data


def get_provider_id(user_id: str) -> int:
    """
    get provider_id from OMOP DB for users issued from ORBIS.
    TODO: check si doit changer avec l'issue de modification du profile id
          par le provider_source_value (id aph du user)
    """
    p: Provider = Provider.objects.filter(Q(provider_source_value=user_id)
                                          & (Q(valid_start_datetime__lte=timezone.now())
                                             | Q(valid_start_datetime__isnull=True))
                                          & (Q(valid_end_datetime__gte=timezone.now())
                                             | Q(valid_end_datetime__isnull=True))).first()
    if p:
        return p.provider_id
    from accesses.models import Profile
    return Profile.objects.aggregate(Max("provider_id"))['provider_id__max'] + 1


class RoleSerializer(BaseSerializer):
    help_text = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = "__all__"
        read_only_fields = ['id']

    def get_help_text(self, role):
        return roles_service.get_help_text(role=role)


class UsersInRoleSerializer(serializers.Serializer):
    provider_username = serializers.CharField(read_only=True)
    firstname = serializers.CharField(read_only=True)
    lastname = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    perimeter = serializers.CharField(read_only=True)
    start_datetime = serializers.CharField(read_only=True)
    end_datetime = serializers.CharField(read_only=True)


class ReducedProfileSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    provider_source_value = serializers.CharField(read_only=True, source='user_id')
    provider_history_id = serializers.IntegerField(read_only=True, source='id')

    class Meta:
        model = Profile
        fields = ["id",
                  "provider_id",
                  "provider_history_id",
                  "is_valid",
                  "provider_source_value",
                  "user_id",
                  "email",
                  "firstname",
                  "lastname",
                  "source"]


class ProfileSerializer(BaseSerializer):
    provider = ReducedUserSerializer(read_only=True, source='user')
    user = serializers.PrimaryKeyRelatedField(required=False, queryset=User.objects.all())
    is_valid = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(required=False, default=True)
    actual_is_active = serializers.BooleanField(read_only=True)
    actual_valid_start_datetime = serializers.DateTimeField(read_only=True)
    actual_valid_end_datetime = serializers.DateTimeField(read_only=True)
    provider_history_id = serializers.IntegerField(required=False, source='id')
    provider_source_value = serializers.CharField(source='user_id', required=False)
    user_id = serializers.CharField(required=False)

    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ["id",
                            "provider",
                            "source",
                            "is_valid",
                            "actual_is_active",
                            "actual_valid_start_datetime",
                            "actual_valid_end_datetime"
                            ]
        extra_kwargs = {'valid_start_datetime': {'write_only': True},
                        'valid_end_datetime': {'write_only': True},
                        'is_active': {'write_only': True},
                        'manual_valid_start_datetime': {'write_only': True},
                        'manual_valid_end_datetime': {'write_only': True},
                        'manual_is_active': {'write_only': True}
                        }


class ProfileCheckSerializer(serializers.Serializer):
    firstname = serializers.CharField(read_only=True, allow_null=True)
    lastname = serializers.CharField(read_only=True, allow_null=True)
    user_id = serializers.CharField(read_only=True, allow_null=True)
    provider_source_value = serializers.CharField(read_only=True, allow_null=True, source='user_id')
    email = serializers.CharField(read_only=True, allow_null=True)
    user = UserSerializer(read_only=True, allow_null=True)
    manual_profile = ProfileSerializer(read_only=True, allow_null=True)
    # todo : remove when ready
    provider = UserSerializer(read_only=True, allow_null=True)


class PerimeterSerializer(serializers.ModelSerializer):
    parent_id = serializers.CharField(read_only=True, allow_null=True)
    # old fields
    care_site_id = serializers.IntegerField(read_only=True, source='id')
    care_site_name = serializers.CharField(read_only=True, source='name')
    care_site_source_value = serializers.CharField(read_only=True, source='source_value')
    care_site_short_name = serializers.CharField(read_only=True, source='short_name')
    care_site_type_source_value = serializers.CharField(read_only=True, source='type_source_value')
    type = serializers.CharField(allow_null=True, source='type_source_value')
    names = serializers.DictField(allow_null=True, read_only=True, child=serializers.CharField())

    class Meta:
        model = Perimeter
        exclude = ["parent"]


class PerimeterLiteSerializer(serializers.ModelSerializer):
    parent_id = serializers.CharField(read_only=True, allow_null=True)
    type = serializers.CharField(allow_null=True, source='type_source_value')

    class Meta:
        model = Perimeter
        fields = ['id',
                  'name',
                  'source_value',
                  'parent_id',
                  'type',
                  'above_levels_ids',
                  'inferior_levels_ids',
                  'cohort_id',
                  'cohort_size',
                  'full_path']


class CareSiteSerializer(serializers.Serializer):
    care_site_id = serializers.CharField(read_only=True)
    care_site_name = serializers.CharField(read_only=True)
    care_site_short_name = serializers.CharField(read_only=True)
    care_site_type_source_value = serializers.CharField(read_only=True)
    care_site_source_value = serializers.CharField(read_only=True)


class AccessSerializer(BaseSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    actual_start_datetime = serializers.DateTimeField(read_only=True, source="start_datetime")
    actual_end_datetime = serializers.DateTimeField(read_only=True, source="end_datetime")
    perimeter = PerimeterSerializer(allow_null=True, required=False)
    perimeter_id = serializers.PrimaryKeyRelatedField(queryset=Perimeter.objects.all(), source="perimeter")
    # todo : remove when ready with perimeter
    care_site = CareSiteSerializer(allow_null=True, required=False, source='perimeter')
    care_site_history_id = serializers.IntegerField(read_only=True, source='id')
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), source="role", write_only=True)
    profile = ReducedProfileSerializer(read_only=True)
    profile_id = serializers.PrimaryKeyRelatedField(queryset=Profile.objects.all(), source="profile", write_only=True)
    provider_history_id = serializers.IntegerField(source='profile_id', required=False)
    provider_history = ReducedProfileSerializer(read_only=True, source='profile')
    created_by = serializers.SlugRelatedField(read_only=True, slug_field="displayed_name")
    updated_by = serializers.SlugRelatedField(read_only=True, slug_field="displayed_name")
    editable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Access
        fields = ["id",
                  "is_valid",
                  "provider_history",
                  "profile",
                  "profile_id",
                  "care_site",
                  "role",
                  "actual_start_datetime",
                  "actual_end_datetime",
                  "start_datetime",
                  "end_datetime",
                  "care_site_id",
                  "provider_history_id",
                  "role_id",
                  "perimeter",
                  "perimeter_id",
                  "care_site_history_id",
                  "created_by",
                  "updated_by",
                  "editable"]
        write_only_fields = ["start_datetime", "end_datetime"]
        read_only_fields = ["_id",
                            "is_valid",
                            "provider",
                            "care_site",
                            "actual_start_datetime",
                            "actual_end_datetime",
                            "role",
                            "perimeter",
                            "profile_id",
                            "care_site_history_id"]

    def create(self, validated_data):
        creator = self.context.get('request').user
        validated_data.update({"created_by": creator,
                               "updated_by": creator})

        validated_data = fix_access_dates(validated_data)
        check_date_rules(new_start_datetime=validated_data.get("start_datetime"),
                         new_end_datetime=validated_data.get("end_datetime"))
        return super(AccessSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("role_id", None)
        validated_data.pop("role", None)
        validated_data.pop("perimeter_id", None)
        validated_data.pop("care_site_id", None)    # todo: remove when ready with perimeter
        validated_data.pop("profile", None)
        validated_data.pop("provider_history_id", None)
        validated_data["updated_by"] = self.context.get('request').user

        validated_data = fix_access_dates(validated_data, for_update=True)
        check_date_rules(new_start_datetime=validated_data.get("start_datetime"),
                         new_end_datetime=validated_data.get("end_datetime"),
                         old_start_datetime=instance.start_datetime,
                         old_end_datetime=instance.end_datetime)
        if validated_data:
            return super(AccessSerializer, self).update(instance, validated_data)
        return instance


class ExpiringAccessesSerializer(serializers.Serializer):
    start_datetime = serializers.DateTimeField(read_only=True)
    end_datetime = serializers.DateTimeField(read_only=True)
    profile = serializers.SlugRelatedField(slug_field='provider_name', read_only=True)
    perimeter = serializers.SlugRelatedField(slug_field='name', read_only=True)


class DataRightSerializer(serializers.Serializer):
    user_id = serializers.CharField(read_only=True, allow_null=True)
    perimeter_id = serializers.CharField(read_only=True, allow_null=True)
    right_read_patient_nominative = serializers.BooleanField(read_only=True, allow_null=True)
    right_read_patient_pseudonymized = serializers.BooleanField(read_only=True, allow_null=True)
    right_search_patients_by_ipp = serializers.BooleanField(read_only=True, allow_null=True)
    right_search_opposed_patients = serializers.BooleanField(read_only=True, allow_null=True)
    right_export_csv_nominative = serializers.BooleanField(read_only=True, allow_null=True)
    right_export_csv_pseudonymized = serializers.BooleanField(read_only=True, allow_null=True)
    right_export_jupyter_nominative = serializers.BooleanField(read_only=True, allow_null=True)
    right_export_jupyter_pseudonymized = serializers.BooleanField(read_only=True, allow_null=True)


class ReadRightPerimeter(serializers.Serializer):
    perimeter = PerimeterLiteSerializer(read_only=True, allow_null=True)
    read_role = serializers.CharField(read_only=True, allow_null=True)
    right_read_patient_nominative = serializers.BooleanField(read_only=True, allow_null=True)
    right_read_patient_pseudonymized = serializers.BooleanField(read_only=True, allow_null=True)
    right_search_patients_by_ipp = serializers.BooleanField(read_only=True, allow_null=True)
    right_read_opposed_patients_data = serializers.BooleanField(read_only=True, allow_null=True)

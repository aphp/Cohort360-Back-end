import logging
import re
from datetime import timedelta
from typing import List

from django.db.models import Max, Q
from django.utils import timezone
from django.utils.datetime_safe import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied

from admin_cohort.auth.utils import check_id_aph
from admin_cohort.models import User
from admin_cohort.serializers import BaseSerializer, ReducedUserSerializer, UserSerializer
from admin_cohort.settings import MANUAL_SOURCE, MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS
from .conf_perimeters import Provider
from .models import Role, Access, Profile, Perimeter
from .permissions import can_user_manage_access

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


def fix_csh_dates(validated_data, for_update: bool = False):
    start_datetime = validated_data.pop("start_datetime", 0)
    end_datetime = validated_data.pop("end_datetime", 0)

    start_is_empty = start_datetime == 0
    end_is_empty = end_datetime == 0

    # if creating a csh, then start_date will be now() if empty or null
    if not for_update:
        validated_data["manual_start_datetime"] = start_datetime \
            if start_datetime is not None and not start_is_empty \
            else timezone.now()
    # if updating a csh, then start_date will be now() if null
    elif not start_is_empty:
        validated_data["manual_start_datetime"] = start_datetime \
            if start_datetime is not None \
            else timezone.now()

    # we deny it if is for updating, and end_datetime has been set to null
    if not end_is_empty and end_datetime is None and for_update:
        raise ValidationError("You cannot set end_datetime "
                              "at null when updating")

    # if there is no value, and it is not for updating, we set end_datetime
    if end_datetime != 0 or not for_update:
        validated_data["manual_end_datetime"] = end_datetime \
            if end_datetime is not None and not end_is_empty \
            else validated_data["manual_start_datetime"] + timedelta(days=MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS)

    return validated_data


def check_profile_entries(validated_data):
    source = validated_data.pop("source", validated_data.pop("cdm_source", MANUAL_SOURCE))
    firstname = validated_data.get("firstname")
    lastname = validated_data.get("lastname")
    email = validated_data.get("email")

    assert all([v and isinstance(v, str) for v in (firstname, lastname, email)]), "Basic info fields must be strings"

    name_regex_pattern = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ\-' ]*$")
    email_regex_pattern = re.compile(r"^[A-Za-z0-9\-. @_]*$")

    if source != MANUAL_SOURCE:
        raise ValidationError(f"Unexpected value for `source`. Takes only: {MANUAL_SOURCE}")

    if firstname and lastname and not name_regex_pattern.match(f"{firstname + lastname}"):
        raise ValidationError("Le nom/prénom fourni est invalide. Doit comporter "
                              "uniquement des lettres et des caractères ' et - ")
    if email and not email_regex_pattern.match(email):
        raise ValidationError(f"L'adresse email fournie ({email}) est invalide. Doit comporter "
                              f"uniquement des lettres, chiffres et caractères @_-.")


def fix_profile_entries(validated_data, for_create: bool = False):
    is_active = validated_data.get("is_active")
    valid_start_datetime = validated_data.get("valid_start_datetime")
    valid_end_datetime = validated_data.get("valid_end_datetime")

    if for_create:
        now = timezone.now()
        validated_data["manual_is_active"] = True
        validated_data["valid_start_datetime"] = now
        validated_data["manual_valid_start_datetime"] = now
        return validated_data

    if is_active is not None:
        validated_data["manual_is_active"] = is_active
    if valid_start_datetime:
        validated_data["manual_valid_start_datetime"] = valid_start_datetime
    if valid_end_datetime:
        validated_data["manual_valid_end_datetime"] = valid_end_datetime

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
    role_id = serializers.IntegerField(source='id', read_only=True)
    help_text = serializers.ListSerializer(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Role
        fields = "__all__"
        read_only_fields = ['id']


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
    cdm_source = serializers.CharField(read_only=True, allow_null=True, source='source')
    provider_source_value = serializers.CharField(source='user_id', required=False)
    user_id = serializers.CharField(required=False)

    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ["id",
                            "provider",
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

    def create(self, validated_data):
        user_id = validated_data.get("user_id")
        assert user_id, "Must provide 'user_id' to create a new profile"

        check_profile_entries(validated_data)
        validated_data = fix_profile_entries(validated_data, for_create=True)

        check_id_aph(user_id)
        try:
            user = User.objects.get(provider_username=user_id)
        except User.DoesNotExist:
            user_data = {"firstname": validated_data.get('firstname'),
                         "lastname": validated_data.get('lastname'),
                         "email": validated_data.get('email'),
                         "provider_username": user_id,
                         "provider_id": user_id
                         }
            user = User.objects.create(**user_data)
        validated_data.update({'user': user,
                               'provider_name': f"{validated_data.get('firstname')} {validated_data.get('lastname')}",
                               'provider_id': user_id
                               })
        return super(ProfileSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        # can only update manual_is_active, manual_valid_start_datetime
        # and manual_valid_end_datetime if ph not manual
        if instance.source == MANUAL_SOURCE:
            check_profile_entries(validated_data)
        validated_data = fix_profile_entries(validated_data)
        return super(ProfileSerializer, self).update(instance, validated_data)


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
    parents_ids = serializers.SerializerMethodField('build_parents_ids', read_only=True)
    type = serializers.CharField(allow_null=True, source='type_source_value')
    names = serializers.DictField(allow_null=True, read_only=True, child=serializers.CharField())
    same_level_users_count = serializers.IntegerField(read_only=True)
    same_and_inf_level_users_count = serializers.IntegerField(read_only=True)

    def build_parents_ids(self, cs: Perimeter) -> List[int]:
        p_id = getattr(cs, 'parent_id', None)
        return [p_id] if p_id else []

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
    actual_start_datetime = serializers.DateTimeField(read_only=True)
    actual_end_datetime = serializers.DateTimeField(read_only=True)
    perimeter = PerimeterSerializer(allow_null=True, required=False)
    perimeter_id = serializers.CharField(allow_null=True, required=False)
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

    class Meta:
        model = Access
        fields = ["id",
                  "is_valid",
                  "provider_history",
                  "profile",
                  "profile_id",
                  "care_site",
                  "role",
                  "start_datetime",
                  "end_datetime",
                  "actual_start_datetime",
                  "actual_end_datetime",
                  "care_site_id",
                  "provider_history_id",
                  "role_id",
                  "perimeter",
                  "perimeter_id",
                  "care_site_history_id",
                  "created_by",
                  "updated_by"]
        write_only_fields = ["start_datetime", "end_datetime"]
        read_only_fields = ["_id",
                            "is_valid",
                            "provider",
                            "care_site",
                            "role",
                            "actual_start_datetime",
                            "actual_end_datetime",
                            "perimeter",
                            "profile_id",
                            "care_site_history_id"]

    def create(self, validated_data):
        creator: User = self.context.get('request').user

        # todo : remove/fix when ready with perimeter
        if 'perimeter' not in validated_data:
            perimeter_id = validated_data.get("perimeter_id", validated_data.pop("care_site_id", None))
            if not perimeter_id:
                raise ValidationError("Requires perimeter")
            try:
                perimeter = Perimeter.objects.get(id=perimeter_id)
            except Perimeter.DoesNotExist:
                raise ValidationError(f"No perimeter found matching the provided ID: {perimeter_id}")
        else:
            perimeter: Perimeter = validated_data.get('perimeter')

        role: Role = validated_data.get('role')
        if not role:
            raise ValidationError("Role field is missing")

        if not can_user_manage_access(creator, role, perimeter):
            raise PermissionDenied("You are not allowed to manage accesses")

        validated_data["created_by"] = creator
        validated_data["updated_by"] = creator

        profile: Profile = validated_data.get("profile")
        provider_history_id = validated_data.get("provider_history_id")
        if not (profile or Profile.objects.filter(id=provider_history_id, source=MANUAL_SOURCE).first()):
            raise ValidationError(f"No profile found matching the provided `provider_history_id`: {provider_history_id}")

        role_id = validated_data.get("role_id")
        if not (role or Role.objects.filter(id=role_id).first()):
            raise ValidationError(f"No role found matching the provided ID: {role_id}")

        validated_data = fix_csh_dates(validated_data)
        check_date_rules(new_start_datetime=validated_data.get("manual_start_datetime"),
                         new_end_datetime=validated_data.get("manual_end_datetime"))

        # todo : remove/fix when ready with perimeter
        validated_data["perimeter_id"] = perimeter_id
        validated_data["perimeter"] = perimeter

        return super(AccessSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("role_id", None)
        validated_data.pop("role", None)
        validated_data.pop("perimeter_id", None)
        validated_data.pop("care_site_id", None)    # todo: remove when ready with perimeter
        validated_data.pop("profile", None)
        validated_data.pop("provider_history_id", None)
        validated_data["updated_by"] = self.context.get('request').user

        validated_data = fix_csh_dates(validated_data, for_update=True)
        check_date_rules(new_start_datetime=validated_data.get("manual_start_datetime"),
                         new_end_datetime=validated_data.get("manual_end_datetime"),
                         old_start_datetime=instance.actual_start_datetime,
                         old_end_datetime=instance.actual_end_datetime)
        if validated_data:
            return super(AccessSerializer, self).update(instance, validated_data)
        return instance


class ExpiringAccessesSerializer(serializers.Serializer):
    start_datetime = serializers.DateTimeField(source='actual_start_datetime', read_only=True)
    end_datetime = serializers.DateTimeField(source='actual_end_datetime', read_only=True)
    profile = serializers.SlugRelatedField(slug_field='provider_name', read_only=True)
    perimeter = serializers.SlugRelatedField(slug_field='name', read_only=True)


class DataRightSerializer(serializers.Serializer):
    perimeter_id = serializers.CharField(read_only=True, allow_null=True)
    care_site_id = serializers.IntegerField(read_only=True, allow_null=True)
    provider_id = serializers.CharField(read_only=True, allow_null=True)
    care_site_history_ids = serializers.ListSerializer(child=serializers.IntegerField(read_only=True, allow_null=True), allow_empty=True)
    access_ids = serializers.ListSerializer(child=serializers.IntegerField(read_only=True, allow_null=True), allow_empty=True)
    right_read_patient_nominative = serializers.BooleanField(read_only=True, allow_null=True)
    right_read_patient_pseudo_anonymised = serializers.BooleanField(read_only=True, allow_null=True)
    right_search_patient_with_ipp = serializers.BooleanField(read_only=True, allow_null=True)
    right_export_csv_nominative = serializers.BooleanField(read_only=True, allow_null=True)
    right_export_csv_pseudo_anonymised = serializers.BooleanField(read_only=True, allow_null=True)
    right_transfer_jupyter_nominative = serializers.BooleanField(read_only=True, allow_null=True)
    right_transfer_jupyter_pseudo_anonymised = serializers.BooleanField(read_only=True, allow_null=True)


class DataReadRightSerializer(serializers.Serializer):
    user_id = serializers.CharField(read_only=True, allow_null=True)
    provider_id = serializers.CharField(read_only=True, allow_null=True)
    perimeter = PerimeterLiteSerializer(allow_null=True, required=False)
    right_read_patient_nominative = serializers.BooleanField(read_only=True, allow_null=True)
    right_read_patient_pseudo_anonymised = serializers.BooleanField(read_only=True, allow_null=True)
    read_role = serializers.CharField(read_only=True, allow_null=True)


class ReadRightPerimeter(serializers.Serializer):
    perimeter = PerimeterLiteSerializer(allow_null=True, required=False)
    read_role = serializers.CharField(read_only=True, allow_null=True)
    right_read_patient_nominative = serializers.BooleanField(read_only=True, allow_null=True)
    right_read_patient_pseudo_anonymised = serializers.BooleanField(read_only=True, allow_null=True)
    right_search_patient_with_ipp = serializers.BooleanField(read_only=True, allow_null=True)

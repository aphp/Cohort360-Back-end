import logging
import re
from datetime import timedelta
from typing import Optional, List

from django.db.models import Max, Q
from django.utils import timezone
from django.utils.datetime_safe import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied

from admin_cohort.conf_auth import check_id_aph
from admin_cohort.models import User
from admin_cohort.serializers import BaseSerializer, ReducedUserSerializer, \
    UserSerializer
from admin_cohort.settings import MODEL_MANUAL_START_DATE_DEFAULT_ON_UPDATE, \
    MODEL_MANUAL_END_DATE_DEFAULT_ON_UPDATE, MANUAL_SOURCE
from .conf_perimeters import Provider
from .models import Role, Access, Profile, Perimeter
from .permissions import can_user_manage_access

_log = logging.getLogger('error')


def check_date_rules(
        new_start_datetime: Optional[datetime] = None,
        new_end_datetime: Optional[datetime] = None,
        old_start_datetime: Optional[datetime] = None,
        old_end_datetime: Optional[datetime] = None
):
    if old_start_datetime is not None:
        # first accesses, added with SQL, may be "naive" (without timezone info)
        old_start = timezone.get_current_timezone().localize(
            old_start_datetime
        ) if getattr(old_start_datetime, "tzinfo", None) is None \
            else old_start_datetime

        if (new_start_datetime is not None
                and new_start_datetime != old_start
                and old_start < timezone.now()):
            raise ValidationError(
                f"La date de début {old_start_datetime} "
                f"ne peut pas être modifiée si elle est passée"
            )
    if old_end_datetime is not None:
        # first accesses, added with SQL, may be "naive" (without timezone info)
        old_end = timezone.get_current_timezone().localize(
            old_end_datetime
        ) if getattr(old_end_datetime, "tzinfo",
                     None) is None else old_end_datetime

        if (new_end_datetime is not None
                and old_end != new_end_datetime
                and old_end < timezone.now()):
            raise ValidationError(
                f"La date de fin {old_end_datetime} ne peut pas être modifiée "
                f"si elle est passée"
            )

    if new_start_datetime is not None \
            and new_start_datetime + timedelta(seconds=10) < timezone.now():
        raise ValidationError(
            f"La date de début {new_start_datetime} ne peut pas être "
            f"dans le passé"
        )
    if new_end_datetime is not None \
            and new_end_datetime + timedelta(seconds=10) < timezone.now():
        raise ValidationError(
            f"La date de fin {new_end_datetime} ne peut pas être "
            f"dans le passé"
        )
    if (new_start_datetime is not None
            and new_end_datetime is not None
            and new_end_datetime < new_start_datetime):
        raise ValidationError(
            f"La date de fin {new_end_datetime} ne peut pas "
            f"précéder la date de début {new_start_datetime}"
        )


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
            else validated_data["manual_start_datetime"] + timedelta(days=365)

    return validated_data


def check_profile_entries(validated_data, for_update: bool = False):
    source = validated_data.pop("source", validated_data.pop('cdm_source', MANUAL_SOURCE))
    firstname = validated_data.get("firstname", -1)
    lastname = validated_data.get("lastname", -1)
    email = validated_data.get("email", -1)

    name_regex_pattern = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ\-' ]*$")
    email_regex_pattern = re.compile(r"^[A-Za-z0-9\-. @_]*$")

    if source != MANUAL_SOURCE:
        raise ValidationError(f"Vous ne pouvez pas définir source sur autre chose que {MANUAL_SOURCE}")

    if firstname != -1:
        if firstname and not name_regex_pattern.match(firstname):
            raise ValidationError(f"Le prénom fourni ({firstname}) est invalide. Doit uniquement "
                                  f"comporter des lettres et des caractères ' et - ")
    if lastname != -1:
        if lastname and not name_regex_pattern.match(lastname):
            raise ValidationError(f"Le nom de famille fourni ({lastname}) est invalide. Doit "
                                  f"uniquement comporter des lettres et des caractères ' et - ")
    if email != -1:
        if email and not email_regex_pattern.match(email):
            raise ValidationError(f"L'adresse email fournie ({email}) est invalide. Doit "
                                  f"uniquement comporter des lettres, chiffres et caractères @_-.")

    user: User = validated_data.get("user", None)

    # if it is for create, we need User detail.
    # else for update we cannot update it
    if for_update:
        return
    if user:
        provider_id = validated_data.get("provider_id", -1)
        if provider_id != -1:
            user: User = User.objects.filter(provider_id=provider_id).first()
            if not user:
                raise ValidationError(f"L'utilisateur avec provider_id='{provider_id}' est introuvable.")
            validated_data['user'] = user
        # this means the user actually needs to create a new user
        else:
            user_id: str = validated_data.get("user_id", validated_data.get("provider_source_value", None))
            if not user_id:
                raise ValidationError("Aucun user ni user_id n'a été fourni.")
            user: User = User.objects.filter(provider_username=user_id).first()
            if user:
                validated_data['user'] = user
            else:
                # we prepare user_id for creating a User
                validated_data['user_id'] = user_id

    if user and any([p.source == MANUAL_SOURCE for p in user.valid_profiles]):
        raise ValidationError(f"L'utilisateur fourni pour le profil possède déjà un profil de source {MANUAL_SOURCE}.")


def fix_profile_entries(validated_data, for_create: bool = False):
    is_active = validated_data.pop("is_active", -1)
    manual_is_active = validated_data.pop("manual_is_active", -1)
    valid_start_datetime = validated_data.pop("valid_start_datetime", -1)
    manual_valid_start_datetime = validated_data.get("manual_valid_start_datetime", -1)
    valid_end_datetime = validated_data.pop("valid_end_datetime", -1)
    manual_valid_end_datetime = validated_data.pop("manual_valid_end_datetime", -1)

    if is_active != -1:
        if manual_is_active != -1 and is_active != manual_is_active:
            raise ValidationError("Vous ne pouvez pas fournir à la fois 'is_active' et 'manual_is_active' différents")
        else:
            validated_data["manual_is_active"] = is_active
    elif manual_is_active != -1:
        validated_data["manual_is_active"] = manual_is_active
    else:
        if for_create:
            validated_data["manual_is_active"] = True

    if valid_start_datetime != -1:
        if manual_valid_start_datetime != -1 and valid_start_datetime != manual_valid_start_datetime:
            raise ValidationError("Vous ne pouvez pas fournir à la fois 'valid_start_datetime'"
                                  " et 'manual_valid_start_datetime' différents")
        else:
            validated_data["manual_valid_start_datetime"] = valid_start_datetime or \
                                                            MODEL_MANUAL_START_DATE_DEFAULT_ON_UPDATE
    elif manual_valid_start_datetime != -1:
        validated_data["manual_valid_start_datetime"] = manual_valid_start_datetime or \
                                                        MODEL_MANUAL_START_DATE_DEFAULT_ON_UPDATE
    if valid_end_datetime != -1:
        if manual_valid_end_datetime != -1 and valid_end_datetime != manual_valid_end_datetime:
            raise ValidationError("Vous ne pouvez pas fournir à la fois 'valid_end_datetime'"
                                  " et 'manual_valid_end_datetime' différents")
        else:
            validated_data["manual_valid_end_datetime"] = valid_end_datetime or \
                                                          MODEL_MANUAL_START_DATE_DEFAULT_ON_UPDATE
    elif manual_valid_end_datetime != -1:
        validated_data["manual_valid_end_datetime"] = manual_valid_end_datetime or \
                                                      MODEL_MANUAL_END_DATE_DEFAULT_ON_UPDATE
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
    help_text = serializers.ListSerializer(
        child=serializers.CharField(), read_only=True)

    class Meta:
        model = Role
        fields = "__all__"
        read_only_fields = ['id']


class ReducedProfileSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    provider_source_value = serializers.CharField(read_only=True,
                                                  source='user_id')
    provider_history_id = serializers.IntegerField(read_only=True, source='id')

    class Meta:
        model = Profile
        fields = [
            "id",
            "provider_id",
            "provider_history_id",
            "is_valid",
            "provider_source_value",
            "user_id",
            "email",
            "firstname",
            "lastname",
            "source"
        ]


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
                            "creation_datetime",
                            "modified_datetime",
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
        check_profile_entries(validated_data)
        validated_data = fix_profile_entries(validated_data, True)

        if 'user' not in validated_data:
            if 'user_id' not in validated_data:
                raise ValidationError("Besoin de soit 'user' soit 'user_id'.")
            user_id = validated_data.get('user_id')
            # calling check_id_aph() a 2nd time to ensure user identity in case of a delay btw entering id_aph
            # and click on "Valider" when adding a user as it might get deleted from AD meanwhile
            try:
                id_details = check_id_aph(user_id)
            except Exception as e:
                _log.exception(str(e))
                raise ValidationError("Echec de la vérification de l'identifiant")

            if not id_details:
                raise ValidationError("Le Provider_source_value/user_id indiqué n'appartient à "
                                      "aucun utilisateur dans la base de données de référence")
            try:
                provider_id = get_provider_id(user_id)
            except Exception:
                raise ValidationError("Le provider_id de ce nouvel utilisateur "
                                      "n'a pas pu être trouvé dans la base OMOP.")

            user_data = {"provider_username": user_id,
                         "email": validated_data.get('email'),
                         "firstname": validated_data.get('firstname'),
                         "lastname": validated_data.get('lastname'),
                         "provider_id": provider_id}
            user = User(**user_data)
            user.save()
            validated_data['user'] = user
            validated_data['provider_id'] = provider_id
            validated_data['provider_name'] = f"{validated_data.get('firstname')} {validated_data.get('lastname')}"
        return super(ProfileSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        # can only update manual_is_active, manual_valid_start_datetime
        # and manual_valid_end_datetime if ph not manual
        if instance.source == MANUAL_SOURCE:
            check_profile_entries(validated_data, True)
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


class TreefiedPerimeterSerializer(serializers.ModelSerializer):
    parent_id = serializers.CharField(read_only=True, allow_null=True)
    names = serializers.DictField(allow_null=True, read_only=True, child=serializers.CharField())
    type = serializers.CharField(allow_null=True, source='type_source_value')

    class Meta:
        model = Perimeter
        exclude = ['insert_datetime', 'update_datetime', 'delete_datetime']

    def get_fields(self):
        fields = super(TreefiedPerimeterSerializer, self).get_fields()
        fields['children'] = TreefiedPerimeterSerializer(many=True, source='prefetched_children', required=False)
        return fields


class YasgTreefiedPerimeterSerializer(TreefiedPerimeterSerializer):
    children = serializers.ListSerializer(child=serializers.JSONField())

    def get_fields(self):
        return super(TreefiedPerimeterSerializer, self).get_fields()


class PerimeterSerializer(serializers.ModelSerializer):
    parent_id = serializers.CharField(read_only=True, allow_null=True)

    # old fields
    care_site_id = serializers.IntegerField(read_only=True, source='id')
    care_site_name = serializers.CharField(read_only=True, source='name')
    care_site_source_value = serializers.CharField(
        read_only=True, source='source_value')
    care_site_short_name = serializers.CharField(
        read_only=True, source='short_name')
    care_site_type_source_value = serializers.CharField(
        read_only=True, source='type_source_value')

    parents_ids = serializers.SerializerMethodField(
        'build_parents_ids', read_only=True)

    type = serializers.CharField(allow_null=True, source='type_source_value')
    names = serializers.DictField(allow_null=True, read_only=True,
                                  child=serializers.CharField())

    def build_parents_ids(self, cs: Perimeter) -> List[int]:
        p_id = getattr(cs, 'parent_id', None)
        return [p_id] if p_id else []

    class Meta:
        model = Perimeter
        exclude = ["parent", "above_levels_ids", "inferior_levels_ids"]


"""
Serializer with minimal config field for perimeters/manageable path
"""


class PerimeterLiteSerializer(serializers.ModelSerializer):
    parent_id = serializers.CharField(read_only=True, allow_null=True)
    type = serializers.CharField(allow_null=True, source='type_source_value')

    class Meta:
        model = Perimeter
        fields = ['id', 'name', 'source_value', 'parent_id', 'type', 'inferior_levels_ids', 'cohort_id', 'cohort_size',
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
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source="role", write_only=True)

    profile = ReducedProfileSerializer(read_only=True)
    profile_id = serializers.PrimaryKeyRelatedField(queryset=Profile.objects.all(), source="profile", write_only=True)
    provider_history_id = serializers.IntegerField(source='profile_id', required=False)
    provider_history = ReducedProfileSerializer(read_only=True, source='profile')

    class Meta:
        model = Access
        fields = [
            "id",
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
        ]
        write_only_fields = ["start_datetime", "end_datetime"]
        read_only_fields = [
            "_id",
            "is_valid",
            "provider",
            "care_site",
            "role",
            "actual_start_datetime",
            "actual_end_datetime",
            "perimeter",
            "profile_id",
            "care_site_history_id",
        ]

    def create(self, validated_data):
        creator: User = self.context.get('request').user

        # todo : remove/fix when ready with perimeter
        if 'perimeter' not in validated_data:
            perimeter_id = validated_data.get(
                "perimeter_id", validated_data.pop("care_site_id", None))
            if perimeter_id is None:
                raise ValidationError("Requires perimeter")
            perimeter = Perimeter.objects.filter(id=perimeter_id).first()
            if perimeter is None:
                raise ValidationError(
                    f"Perimeter id provided ({perimeter_id}) does not match"
                    f" existing any perimeter"
                )
        else:
            perimeter: Perimeter = validated_data.get('perimeter', None)

        role: Role = validated_data.get('role', None)
        if not role:
            raise ValidationError("Role field is missing")

        if not can_user_manage_access(creator, role, perimeter):
            raise PermissionDenied

        profile: Profile = validated_data.get("profile", None)
        provider_history_id = validated_data.get("provider_history_id", None)
        if profile is None and Profile.objects.filter(
                id=provider_history_id,
                source=MANUAL_SOURCE
        ).first() is None:
            raise ValidationError(
                f"Provider_history_id provided ({provider_history_id}) does not"
                f" match an existing manual provider history"
            )

        role: Role = validated_data.get("role", None)
        role_id = validated_data.get("role_id", None)
        if role is None and Role.objects.filter(id=role_id).first() is None:
            raise ValidationError(
                f"Role id provided ({role_id}) does not match existing any role"
            )

        validated_data = fix_csh_dates(validated_data)
        check_date_rules(
            validated_data.get("manual_start_datetime", None),
            validated_data.get("manual_end_datetime", None)
        )

        # todo : remove/fix when ready with perimeter
        validated_data["perimeter_id"] = perimeter_id
        validated_data["perimeter"] = perimeter

        return super(AccessSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        # these fields cannot be updated, user has to close the
        # Access and create a new one
        validated_data.pop("role_id", None)
        validated_data.pop("role", None)
        validated_data.pop("perimeter_id", None)
        # todo : remove when ready with perimeter
        validated_data.pop("care_site_id", None)
        validated_data.pop("profile", None)
        validated_data.pop("provider_history_id", None)

        # no default values when update partially
        validated_data = fix_csh_dates(validated_data, True)
        check_date_rules(
            validated_data.get("manual_start_datetime"),
            validated_data.get("manual_end_datetime"),
            instance.actual_start_datetime, instance.actual_end_datetime
        )

        instance = super(AccessSerializer, self).update(
            instance, validated_data
        ) if len(validated_data) > 0 else instance

        return instance


class DataRightSerializer(serializers.Serializer):
    perimeter_id = serializers.CharField(read_only=True, allow_null=True)
    care_site_id = serializers.IntegerField(read_only=True, allow_null=True)
    provider_id = serializers.IntegerField(read_only=True, allow_null=True)
    care_site_history_ids = serializers.ListSerializer(
        child=serializers.IntegerField(read_only=True, allow_null=True),
        allow_empty=True
    )
    access_ids = serializers.ListSerializer(
        child=serializers.IntegerField(read_only=True, allow_null=True),
        allow_empty=True
    )
    right_read_patient_nominative = serializers.BooleanField(read_only=True,
                                                             allow_null=True)
    right_read_patient_pseudo_anonymised = serializers.BooleanField(
        read_only=True, allow_null=True)
    right_search_patient_with_ipp = serializers.BooleanField(
        read_only=True, allow_null=True)
    right_export_csv_nominative = serializers.BooleanField(
        read_only=True, allow_null=True)
    right_export_csv_pseudo_anonymised = serializers.BooleanField(
        read_only=True, allow_null=True)
    right_transfer_jupyter_nominative = serializers.BooleanField(
        read_only=True, allow_null=True)
    right_transfer_jupyter_pseudo_anonymised = serializers.BooleanField(
        read_only=True, allow_null=True)


class DataReadRightSerializer(serializers.Serializer):
    user_id = serializers.CharField(read_only=True, allow_null=True)
    provider_id = serializers.IntegerField(read_only=True, allow_null=True)
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

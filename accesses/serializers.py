import logging

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from admin_cohort.serializers import BaseSerializer, UserSerializer
from accesses.models import Role, Access, Profile, Perimeter, Right
from accesses.services.roles import roles_service

_logger = logging.getLogger('django.request')


class RightSerializer(ModelSerializer):
    depends_on = serializers.SlugRelatedField(slug_field='name', queryset=Right.objects.all(), required=False)

    class Meta:
        model = Right
        fields = ["name",
                  "label",
                  "depends_on",
                  "category",
                  "is_global",
                  "allow_read_accesses_on_same_level",
                  "allow_read_accesses_on_inf_levels",
                  "allow_edit_accesses_on_same_level",
                  "allow_edit_accesses_on_inf_levels",
                  "impact_inferior_levels"
                  ]
        extra_kwargs = {'allow_read_accesses_on_same_level': {'write_only': True},
                        'allow_read_accesses_on_inf_levels': {'write_only': True},
                        'allow_edit_accesses_on_same_level': {'write_only': True},
                        'allow_edit_accesses_on_inf_levels': {'write_only': True},
                        'impact_inferior_levels': {'write_only': True}
                        }


class RoleSerializer(BaseSerializer):
    help_text = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = "__all__"
        read_only_fields = ['id']

    def get_help_text(self, role):
        return roles_service.get_help_text(role=role)


class UsersInRoleSerializer(serializers.Serializer):
    provider_username = serializers.CharField(read_only=True, source="username")
    firstname = serializers.CharField(read_only=True)
    lastname = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    perimeter = serializers.CharField(read_only=True)
    start_datetime = serializers.CharField(read_only=True)
    end_datetime = serializers.CharField(read_only=True)


class ReducedProfileSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    username = serializers.CharField(read_only=True, source='user_id')
    provider_id = serializers.CharField(required=False, source="user_id")
    firstname = serializers.CharField(required=False, source="user.firstname")
    lastname = serializers.CharField(required=False, source="user.lastname")
    email = serializers.CharField(required=False, source="user.email")


    class Meta:
        model = Profile
        fields = ["id",
                  "provider_id",
                  "is_valid",
                  "username",
                  "email",
                  "firstname",
                  "lastname",
                  "source"]


class ProfileSerializer(BaseSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(required=False, default=True)
    actual_is_active = serializers.BooleanField(read_only=True)
    actual_valid_start_datetime = serializers.DateTimeField(read_only=True)
    actual_valid_end_datetime = serializers.DateTimeField(read_only=True)
    user_id = serializers.CharField(required=False)
    firstname = serializers.CharField(read_only=True, source="user.firstname")
    lastname = serializers.CharField(read_only=True, source="user.lastname")
    email = serializers.CharField(read_only=True, source="user.email")
    provider_id = serializers.CharField(read_only=True, source="user_id")
    provider_name = serializers.CharField(read_only=True, source="user.display_name")

    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ["id",
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
    firstname = serializers.CharField(read_only=True)
    lastname = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)
    manual_profile = ProfileSerializer(read_only=True)


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
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), source="role", write_only=True)
    profile = ReducedProfileSerializer(read_only=True)
    profile_id = serializers.PrimaryKeyRelatedField(queryset=Profile.objects.all(), source="profile", write_only=True)
    created_by = serializers.SlugRelatedField(read_only=True, slug_field="display_name")
    updated_by = serializers.SlugRelatedField(read_only=True, slug_field="display_name")
    editable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Access
        fields = ["id",
                  "is_valid",
                  "profile",
                  "profile_id",
                  "care_site",
                  "role",
                  "actual_start_datetime",
                  "actual_end_datetime",
                  "start_datetime",
                  "end_datetime",
                  "care_site_id",
                  "role_id",
                  "perimeter",
                  "perimeter_id",
                  "created_by",
                  "updated_by",
                  "editable"]
        write_only_fields = ["start_datetime", "end_datetime"]
        read_only_fields = ["is_valid",
                            "care_site",
                            "actual_start_datetime",
                            "actual_end_datetime",
                            "role",
                            "perimeter",
                            "profile_id"]

    def create(self, validated_data):
        creator = self.context.get('request').user
        validated_data.update({"created_by": creator,
                               "updated_by": creator})
        return super(AccessSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context.get('request').user
        return super(AccessSerializer, self).update(instance, validated_data)


class ExpiringAccessesSerializer(serializers.Serializer):
    start_datetime = serializers.DateTimeField(read_only=True)
    end_datetime = serializers.DateTimeField(read_only=True)
    profile = serializers.SerializerMethodField()
    perimeter = serializers.SlugRelatedField(slug_field='name', read_only=True)

    def get_profile(self, access):
        return access.profile.user.display_name


class DataRightSerializer(serializers.Serializer):
    user_id = serializers.CharField(read_only=True, allow_null=True)
    perimeter_id = serializers.IntegerField(read_only=True, allow_null=True)
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

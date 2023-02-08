from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_tracking.models import APIRequestLog

from admin_cohort.models import MaintenancePhase
from admin_cohort.models import User


class UserDetailsSerializer(serializers.Serializer):
    firstname = serializers.CharField()
    lastname = serializers.CharField()
    displayed_name = serializers.CharField()
    email = serializers.CharField()
    provider_id = serializers.CharField()


class APIRequestLogSerializer(serializers.ModelSerializer):
    related_names = serializers.DictField(read_only=True)
    user_details = UserDetailsSerializer(allow_null=True)

    class Meta:
        model = APIRequestLog
        fields = [f.name for f in APIRequestLog._meta.fields] + [
            "related_names",
            "user_details",
        ]


class BaseSerializer(serializers.ModelSerializer):
    insert_datetime = serializers.DateTimeField(read_only=True)
    update_datetime = serializers.DateTimeField(read_only=True)
    delete_datetime = serializers.DateTimeField(read_only=True)


class OmopBaseSerializer(BaseSerializer):
    def create(self, validated_data):
        validated_data["hash"] = 0
        return super(OmopBaseSerializer, self).create(validated_data)


class ReducedUserSerializer(serializers.ModelSerializer):
    provider_source_value = serializers.CharField(read_only=True, source="provider_username")

    class Meta:
        model = User
        fields = ["provider_id",
                  "provider_username",
                  "email",
                  "firstname",
                  "lastname",
                  "provider_source_value"]


class OpenUserSerializer(serializers.ModelSerializer):
    displayed_name = serializers.CharField(read_only=True)
    provider_source_value = serializers.CharField(read_only=True, source="provider_username")

    class Meta:
        model = User
        fields = ["provider_id",
                  "provider_username",
                  "firstname",
                  "lastname",
                  "provider_source_value",
                  "displayed_name"]


class MaintenanceValidator:
    message = 'end_datetime is lower than start_datetime'
    requires_context = True

    def __call__(self, attrs, serializer):
        if serializer.partial:
            inst: MaintenancePhase = serializer.instance
            start = attrs.get('start_datetime', inst.start_datetime)
            end = attrs.get('end_datetime', inst.end_datetime)
        else:
            start = attrs.get('start_datetime')
            end = attrs.get('end_datetime')

        if start > end:
            raise ValidationError(self.message)


class MaintenancePhaseSerializer(BaseSerializer):
    maintenance_start = serializers.DateTimeField(read_only=True, allow_null=True, source='start_datetime')
    maintenance_end = serializers.DateTimeField(read_only=True, allow_null=True, source='end_datetime')
    active = serializers.BooleanField(read_only=True)

    class Meta:
        model = MaintenancePhase
        fields = "__all__"

    def get_validators(self):
        return super(MaintenancePhaseSerializer, self).get_validators() + [MaintenanceValidator()]


class UserSerializer(serializers.ModelSerializer):
    displayed_name = serializers.CharField(read_only=True)
    provider_source_value = serializers.CharField(read_only=True, source="provider_username")

    class Meta:
        model = User
        fields = "__all__"

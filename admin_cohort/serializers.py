from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_tracking.models import APIRequestLog

from admin_cohort.models import MaintenancePhase, User, ReleaseNote


class BaseSerializer(serializers.ModelSerializer):
    insert_datetime = serializers.DateTimeField(read_only=True)
    update_datetime = serializers.DateTimeField(read_only=True)
    delete_datetime = serializers.DateTimeField(read_only=True)


class OmopBaseSerializer(BaseSerializer):
    def create(self, validated_data):
        validated_data["hash"] = 0
        return super(OmopBaseSerializer, self).create(validated_data)


class MaintenanceValidator:
    message = "end_datetime is lower than start_datetime"
    requires_context = True

    def __call__(self, attrs, serializer):
        if serializer.partial:
            inst: MaintenancePhase = serializer.instance
            start = attrs.get("start_datetime", inst.start_datetime)
            end = attrs.get("end_datetime", inst.end_datetime)
        else:
            start = attrs.get("start_datetime")
            end = attrs.get("end_datetime")

        if start > end:
            raise ValidationError(self.message)


class MaintenancePhaseSerializer(BaseSerializer):
    maintenance_start = serializers.DateTimeField(read_only=True, allow_null=True, source="start_datetime")
    maintenance_end = serializers.DateTimeField(read_only=True, allow_null=True, source="end_datetime")
    active = serializers.BooleanField(read_only=True)

    class Meta:
        model = MaintenancePhase
        fields = "__all__"

    def get_validators(self):
        return super(MaintenancePhaseSerializer, self).get_validators() + [MaintenanceValidator()]


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    created_by: serializers.SlugRelatedField = serializers.SlugRelatedField(read_only=True, slug_field="display_name")
    updated_by: serializers.SlugRelatedField = serializers.SlugRelatedField(read_only=True, slug_field="display_name")
    onboarding_step = serializers.IntegerField(read_only=True)
    onboarding_completed_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = User
        fields = ["username", "firstname", "lastname", "email", "password", "display_name", "created_by", "updated_by",
                  "onboarding_step", "onboarding_completed_at"]


class OnboardingSerializer(serializers.ModelSerializer):
    onboarding_step = serializers.IntegerField(min_value=0, max_value=User.ONBOARDING_TOTAL_STEPS)

    class Meta:
        model = User
        fields = ["onboarding_step", "onboarding_completed_at"]
        read_only_fields = ["onboarding_completed_at"]

    def validate_onboarding_step(self, value):
        current = self.instance.onboarding_step if self.instance else 0
        if value < current:
            raise ValidationError("onboarding_step cannot decrease")
        if value > current + 1:
            raise ValidationError("onboarding_step must progress one step at a time")
        return value

    def update(self, instance, validated_data):
        instance.onboarding_step = validated_data["onboarding_step"]
        if instance.onboarding_step >= User.ONBOARDING_TOTAL_STEPS and instance.onboarding_completed_at is None:
            instance.onboarding_completed_at = timezone.now()
        instance.save(update_fields=["onboarding_step", "onboarding_completed_at", "update_datetime"])
        return instance


class UserCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True)
    firstname = serializers.CharField(required=True)
    lastname = serializers.CharField(required=True)
    email = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ["username", "firstname", "lastname", "email"]


class UserPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["firstname", "lastname", "email"]


class UserCheckSerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)
    firstname = serializers.CharField(read_only=True)
    lastname = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    already_exists = serializers.BooleanField(read_only=True)
    found = serializers.BooleanField(read_only=True)


class ReleaseNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleaseNote
        exclude = ("delete_datetime",)


class RequestLogSerializer(serializers.ModelSerializer):
    related_names = serializers.DictField(read_only=True)
    user_details = UserSerializer(allow_null=True)

    class Meta:
        model = APIRequestLog
        fields = "__all__"


class LoginFormSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class LoginSerializer(serializers.Serializer):
    user = UserSerializer(required=True)
    last_login = serializers.DateTimeField(required=True)
    access_token = serializers.CharField(required=True)
    refresh_token = serializers.CharField(required=True)

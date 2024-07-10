from rest_framework import serializers

from admin_cohort.models import User
from admin_cohort.serializers import BaseSerializer, UserSerializer
from admin_cohort.types import MissingDataError
from cohort.models import CohortResult, DatedMeasure, Folder, Request, RequestQuerySnapshot, FhirFilter, FeasibilityStudy, RequestRefreshSchedule


class PrimaryKeyRelatedFieldWithOwner(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context.get("request").user
        if not user:
            raise MissingDataError("No context request provided")
        return super(PrimaryKeyRelatedFieldWithOwner, self).get_queryset().filter(owner=user)


class UserPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context.get("request").user
        if not user:
            raise MissingDataError("No context request provided")
        qs = super(UserPrimaryKeyRelatedField, self).get_queryset()
        return qs.filter(pk=user.pk)


class CohortBaseSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    modified_at = serializers.DateTimeField(read_only=True)
    deleted = serializers.DateTimeField(read_only=True)


class DatedMeasureSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    request = serializers.UUIDField(read_only=True, required=False, source='request_query_snapshot__request__pk')
    request_query_snapshot = PrimaryKeyRelatedFieldWithOwner(queryset=RequestQuerySnapshot.objects.all())
    count_outdated = serializers.BooleanField(read_only=True)
    cohort_limit = serializers.IntegerField(read_only=True)

    class Meta:
        model = DatedMeasure
        fields = "__all__"
        read_only_fields = ["count_task_id",
                            "request_job_id",
                            "mode",
                            "request"]


class CohortResultSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    result_size = serializers.IntegerField(read_only=True)
    request = serializers.UUIDField(read_only=True, required=False, source='request_id')
    request_query_snapshot = PrimaryKeyRelatedFieldWithOwner(queryset=RequestQuerySnapshot.objects.all())
    dated_measure = PrimaryKeyRelatedFieldWithOwner(queryset=DatedMeasure.objects.all())
    dated_measure_global = PrimaryKeyRelatedFieldWithOwner(queryset=DatedMeasure.objects.all(), required=False)
    group_id = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    exportable = serializers.BooleanField(read_only=True)

    class Meta:
        model = CohortResult
        fields = "__all__"
        read_only_fields = ["create_task_id",
                            "request_job_id",
                            "type"]


class CohortResultSerializerFullDatedMeasure(CohortResultSerializer):
    dated_measure = DatedMeasureSerializer(required=False, allow_null=True)
    dated_measure_global = DatedMeasureSerializer(required=False, allow_null=True)


class ReducedCohortResultSerializer(BaseSerializer):
    query_snapshot = serializers.UUIDField(read_only=True, source='request_query_snapshot_id')

    class Meta:
        model = CohortResult
        fields = ["name",
                  "favorite",
                  "request_job_status",
                  "query_snapshot",
                  "result_size",
                  "modified_at",
                  "exportable"]


class ReducedRequestQuerySnapshotSerializer(BaseSerializer):
    cohort_results = ReducedCohortResultSerializer(many=True, read_only=True)

    class Meta:
        model = RequestQuerySnapshot
        fields = ["uuid",
                  "created_at",
                  "title",
                  "has_linked_cohorts",
                  "cohort_results",
                  "version"]


class RequestQuerySnapshotSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    request = PrimaryKeyRelatedFieldWithOwner(queryset=Request.objects.all(), required=False)
    previous_snapshot = PrimaryKeyRelatedFieldWithOwner(required=False, queryset=RequestQuerySnapshot.objects.all())
    dated_measures = DatedMeasureSerializer(many=True, read_only=True)
    cohort_results = CohortResultSerializer(many=True, read_only=True)
    shared_by = UserSerializer(allow_null=True, read_only=True)

    class Meta:
        model = RequestQuerySnapshot
        fields = "__all__"
        read_only_fields = ["dated_measures",
                            "cohort_results",
                            "shared_by"]


class RequestSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    query_snapshots = ReducedRequestQuerySnapshotSerializer(read_only=True, many=True)
    shared_by = UserSerializer(read_only=True)
    parent_folder = PrimaryKeyRelatedFieldWithOwner(queryset=Folder.objects.all())

    class Meta:
        model = Request
        fields = "__all__"
        read_only_fields = ["query_snapshots", 'shared_by']

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res["query_snapshots"] = sorted(res["query_snapshots"],
                                        key=lambda rqs: rqs["created_at"],
                                        reverse=True)
        return res


class FolderSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    requests = serializers.SlugRelatedField(slug_field='uuid', many=True, read_only=True)

    class Meta:
        model = Folder
        fields = "__all__"


class CohortRightsSerializer(serializers.Serializer):
    cohort_id = serializers.CharField(read_only=True, allow_null=False)
    rights = serializers.DictField(read_only=True, allow_null=True)


class FhirFilterSerializer(BaseSerializer):
    owner = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = FhirFilter
        fields = '__all__'

    def create(self, validated_data):
        validated_data["owner"] = self.context.get('request').user
        return super(FhirFilterSerializer, self).create(validated_data)


class FeasibilityStudySerializer(serializers.ModelSerializer):
    class Meta:
        model = FeasibilityStudy
        write_only_fields = ["request_query_snapshot"]
        read_only_fields = ["request_job_id",
                            "report_json_content",
                            "report_file",
                            "request_job_id"]
        exclude = ["request_job_duration",
                   "deleted",
                   "deleted_by_cascade"]


class RequestRefreshScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestRefreshSchedule
        fields = '__all__'
        read_only_fields = ["last_refresh",
                            "last_refresh_succeeded",
                            "last_refresh_count",
                            "last_refresh_error_msg"]

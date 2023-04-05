from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from cohort.tasks import get_count_task, cancel_previously_running_dm_jobs
import cohort.conf_cohort_job_api as cohort_job_api
from admin_cohort.models import User
from admin_cohort.serializers import BaseSerializer, OpenUserSerializer
from admin_cohort.types import JobStatus, MissingDataError
from cohort.models import CohortResult, DatedMeasure, Folder, Request, RequestQuerySnapshot
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.tools import retrieve_perimeters


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
                            "request_job_status",
                            "request_job_fail_msg",
                            "request_job_duration",
                            "mode",
                            "request"]

    def update(self, instance, validated_data):
        for f in ['request_query_snapshot']:
            if f in validated_data:
                raise ValidationError(f'{f} field cannot bu updated manually')
        return super(DatedMeasureSerializer, self).update(instance, validated_data)

    def create(self, validated_data):
        query_snapshot = validated_data.get("request_query_snapshot")
        measure = validated_data.get("measure")
        fhir_datetime = validated_data.get("fhir_datetime")

        if not query_snapshot:
            raise ValidationError("Invalid 'request_query_snapshot_id'")

        if (measure and not fhir_datetime) or (not measure and fhir_datetime):
            raise ValidationError("If you provide measure or fhir_datetime, you have to provide the other")

        auth_header = cohort_job_api.get_authorization_header(self.context.get("request"))
        cancel_previously_running_dm_jobs.delay(auth_header, query_snapshot.uuid)

        dm = super(DatedMeasureSerializer, self).create(validated_data=validated_data)
        if not measure:
            try:
                auth_header = cohort_job_api.get_authorization_header(self.context.get("request"))
                get_count_task.delay(auth_header, query_snapshot.serialized_query, dm.uuid)
            except Exception as e:
                dm.delete()
                raise ValidationError(f"INTERNAL ERROR: Could not launch FHIR cohort count: {e}")
        return dm


class CohortResultSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    result_size = serializers.IntegerField(read_only=True)
    request = serializers.UUIDField(read_only=True, required=False, source='request_id')
    request_query_snapshot = PrimaryKeyRelatedFieldWithOwner(queryset=RequestQuerySnapshot.objects.all())
    dated_measure = PrimaryKeyRelatedFieldWithOwner(queryset=DatedMeasure.objects.all())
    dated_measure_global = PrimaryKeyRelatedFieldWithOwner(queryset=DatedMeasure.objects.all(), required=False)
    global_estimate = serializers.BooleanField(write_only=True, allow_null=True, default=True)
    fhir_group_id = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    exportable = serializers.BooleanField(read_only=True)

    class Meta:
        model = CohortResult
        fields = "__all__"
        read_only_fields = ["create_task_id",
                            "request_job_id",
                            "type"]

    def update(self, instance, validated_data):
        for f in ['owner', 'request_query_snapshot', 'dated_measure', 'type']:
            if f in validated_data:
                raise ValidationError(f'{f} field cannot be updated manually')
        return super(CohortResultSerializer, self).update(instance, validated_data)

    def create(self, validated_data):
        global_estimate = validated_data.pop("global_estimate", None) and \
                          validated_data.get('dated_measure_global') is None
        rqs = validated_data.get("request_query_snapshot")
        dm_global: DatedMeasure = None
        if global_estimate:
            dm_global = DatedMeasure.objects.create(owner=rqs.owner,
                                                    request_query_snapshot=rqs,
                                                    mode=GLOBAL_DM_MODE)
            validated_data["dated_measure_global"] = dm_global

        cohort_result: CohortResult = super(CohortResultSerializer, self).create(validated_data=validated_data)

        if global_estimate:
            try:
                from cohort.tasks import get_count_task
                get_count_task.delay(cohort_job_api.get_authorization_header(self.context.get("request")),
                                     str(rqs.serialized_query),
                                     dm_global.uuid)
            except Exception as e:
                dm_global.request_job_fail_msg = f"ERROR: Could not launch FHIR cohort count: {e}"
                dm_global.request_job_status = JobStatus.failed
                dm_global.save()
        try:
            from cohort.tasks import create_cohort_task
            auth_header = cohort_job_api.get_authorization_header(self.context.get("request"))
            create_cohort_task.delay(auth_header, rqs.serialized_query, cohort_result.uuid)
        except Exception as e:
            cohort_result.delete()
            raise ValidationError(f"Error on pushing new message to the queue: {e}")

        return cohort_result


class CohortResultSerializerFullDatedMeasure(CohortResultSerializer):
    dated_measure = DatedMeasureSerializer(required=False, allow_null=True)
    dated_measure_global = DatedMeasureSerializer(required=False, allow_null=True)


class ReducedRequestQuerySnapshotSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)

    class Meta:
        model = RequestQuerySnapshot
        fields = "__all__"


class RequestQuerySnapshotSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    request = PrimaryKeyRelatedFieldWithOwner(queryset=Request.objects.all(), required=False)
    previous_snapshot = PrimaryKeyRelatedFieldWithOwner(required=False, queryset=RequestQuerySnapshot.objects.all())
    dated_measures = DatedMeasureSerializer(many=True, read_only=True)
    cohort_results = CohortResultSerializer(many=True, read_only=True)
    shared_by = OpenUserSerializer(allow_null=True, read_only=True, source='shared_by.provider')

    class Meta:
        model = RequestQuerySnapshot
        fields = "__all__"
        optional_fields = ["previous_snapshot", "request"]
        read_only_fields = ["is_active_branch", "care_sites_ids",
                            "dated_measures", "cohort_results", 'shared_by']

    def create(self, validated_data):
        previous_snapshot = validated_data.get("previous_snapshot")
        request = validated_data.get("request")
        if previous_snapshot:
            if request and request.uuid != previous_snapshot.request.uuid:
                raise ValidationError("The provided request is different from the previous_snapshot's request")
            validated_data["request"] = previous_snapshot.request
        elif request:
            if len(request.query_snapshots.all()) != 0:
                raise ValidationError("Must provide a previous_snapshot if the request is not empty of snapshots")
        else:
            raise ValidationError("No previous_snapshot or request were provided")

        serialized_query = validated_data.get("serialized_query")
        validated_data["perimeters_ids"] = retrieve_perimeters(serialized_query)

        new_rqs = super(RequestQuerySnapshotSerializer, self).create(validated_data=validated_data)

        if new_rqs.previous_snapshot is not None:
            for rqs in new_rqs.previous_snapshot.next_snapshots.all():
                rqs.is_active_branch = False
                rqs.save()
        return new_rqs

    def update(self, instance, validated_data):
        for f in ['request', 'request_id']:
            if f in validated_data:
                raise ValidationError(f'{f} field cannot be updated manually')
        return super(RequestQuerySnapshotSerializer, self).update(instance, validated_data)


class RequestSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    query_snapshots = serializers.SlugRelatedField(slug_field='uuid', many=True, read_only=True)
    shared_by = OpenUserSerializer(read_only=True)
    parent_folder = PrimaryKeyRelatedFieldWithOwner(queryset=Folder.objects.all())

    class Meta:
        model = Request
        fields = "__all__"
        read_only_fields = ["query_snapshots", 'shared_by']


class FolderSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    requests = serializers.SlugRelatedField(slug_field='uuid', many=True, read_only=True)

    class Meta:
        model = Folder
        fields = "__all__"


class CohortRightsSerializer(serializers.Serializer):
    cohort_id = serializers.CharField(read_only=True, allow_null=False)
    rights = serializers.DictField(read_only=True, allow_null=True)

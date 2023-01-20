import json

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

import cohort.conf_cohort_job_api as conf
from admin_cohort.serializers import BaseSerializer, OpenUserSerializer
from admin_cohort.settings import COHORT_LIMIT
from admin_cohort.types import JobStatus
from cohort.models import Request, CohortResult, RequestQuerySnapshot, DatedMeasure, Folder, GLOBAL_DM_MODE
from cohort.models import User


class PrimaryKeyRelatedFieldWithOwner(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context.get("request").user
        if not user:
            raise Exception("Internal error: No context request provided to serializer")
        return super(PrimaryKeyRelatedFieldWithOwner, self).get_queryset().filter(owner=user)


class UserPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context.get("request").user
        if not user:
            raise Exception("Internal error: No context request provided to serializer")
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

    class Meta:
        model = DatedMeasure
        fields = "__all__"
        optional = []
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
        rqs = validated_data.get("request_query_snapshot", None)
        measure = validated_data.get("measure", None)
        fhir_datetime = validated_data.get("fhir_datetime", None)

        if rqs is None:
            raise ValidationError("You have to provide a request_query_snapshot_id to bind the dated measure to it")

        if (measure is not None and fhir_datetime is None) or (measure is None and fhir_datetime is not None):
            raise ValidationError("If you provide measure or fhir_datetime, you have to provide the other")

        res_dm = super(DatedMeasureSerializer, self).create(validated_data=validated_data)

        if measure is None:
            try:
                from cohort.tasks import get_count_task
                auth_header = conf.get_fhir_authorization_header(self.context.get("request", None))
                json_query = conf.format_json_request(str(rqs.serialized_query))
                get_count_task.delay(auth_header, json_query, res_dm.uuid)
            except Exception as e:
                res_dm.delete()
                raise ValidationError(f"INTERNAL ERROR: Could not launch FHIR cohort count: {e}")
        return res_dm


class CohortResultSerializer(BaseSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    result_size = serializers.IntegerField(read_only=True)
    request = serializers.UUIDField(read_only=True, required=False, source='request_id')
    request_query_snapshot = PrimaryKeyRelatedFieldWithOwner(queryset=RequestQuerySnapshot.objects.all())
    dated_measure = PrimaryKeyRelatedFieldWithOwner(queryset=DatedMeasure.objects.all())
    dated_measure_global = PrimaryKeyRelatedFieldWithOwner(queryset=DatedMeasure.objects.all(), required=False)
    global_estimate = serializers.BooleanField(write_only=True, allow_null=True, default=True)
    fhir_group_id = serializers.CharField(allow_blank=True, allow_null=True, required=False)

    class Meta:
        model = CohortResult
        fields = "__all__"
        read_only_fields = ["create_task_id",
                            "request_job_id",
                            "request_job_status",
                            "request_job_fail_msg",
                            "request_job_duration",
                            "type"]

    def update(self, instance, validated_data):
        for f in ['owner', 'request_query_snapshot', 'dated_measure', 'type']:
            if f in validated_data:
                raise ValidationError(f'{f} field cannot be updated manually')
        return super(CohortResultSerializer, self).update(instance, validated_data)

    def create(self, validated_data):
        global_estimate = validated_data.pop("global_estimate", None) and \
                          validated_data.get('dated_measure_global') \
                          is None

        dm_global: DatedMeasure = None
        if global_estimate:
            rqs = validated_data.get("request_query_snapshot")
            dm_global = DatedMeasure.objects.create(owner=rqs.owner,
                                                    request_query_snapshot=rqs,
                                                    mode=GLOBAL_DM_MODE)
            validated_data["dated_measure_global"] = dm_global

        if validated_data['dated_measure'].measure > COHORT_LIMIT:
            validated_data['request_job_status'] = JobStatus.long_pending

        cohort_result: CohortResult = super(CohortResultSerializer, self).create(validated_data=validated_data)

        if global_estimate:
            try:
                from cohort.tasks import get_count_task
                get_count_task.delay(conf.get_fhir_authorization_header(self.context.get("request")),
                                     conf.format_json_request(str(rqs.serialized_query)),
                                     dm_global.uuid)
            except Exception as e:
                dm_global.request_job_fail_msg = f"ERROR: Could not launch FHIR cohort count: {e}"
                dm_global.request_job_status = JobStatus.failed
                dm_global.save()

        try:
            from cohort.kafka.producer import push_cohort_creation_to_queue
            push_cohort_creation_to_queue(cohort_result_uuid=cohort_result.uuid,
                                          json_query=rqs.serialized_query)
        except Exception as e:
            cohort_result.delete()
            raise ValidationError(f"Error on pushing new message to the queue: {e}")

    # def create(self, validated_data):
    #     if validated_data.get("type", None) is not None:
    #         raise ValidationError("You cannot provide a type")
    #
    #     rqs = validated_data.get("request_query_snapshot", None)
    #     global_estimate = (validated_data.pop("global_estimate", None) and
    #                        validated_data.get('dated_measure_global', None)
    #                        is None)
    #
    #     dm = validated_data.get("dated_measure", dict(fhir_datetime=None, measure=None))
    #     if not isinstance(dm, DatedMeasure):
    #         if "measure" in dm and dm["measure"] is None:
    #             dm = DatedMeasure.objects.create(owner=rqs.owner, request_query_snapshot=rqs)
    #             dm.save()
    #         else:
    #             dm_serializer = DatedMeasureSerializer(data={**dm,
    #                                                          "owner": rqs.owner.provider_username,
    #                                                          "request_query_snapshot": rqs.uuid
    #                                                          }, context=self.context)
    #
    #             dm_serializer.is_valid(raise_exception=True)
    #             dm = dm_serializer.save()
    #         validated_data["dated_measure"] = dm
    #
    #     res_dm_global: DatedMeasure = None
    #     if global_estimate:
    #         res_dm_global: DatedMeasure = DatedMeasure.objects.create(owner=rqs.owner, request_query_snapshot=rqs,
    #                                                                   mode=GLOBAL_DM_MODE)
    #         validated_data["dated_measure_global"] = res_dm_global
    #
    #     result_cr: CohortResult = super(CohortResultSerializer, self).create(validated_data=validated_data)
    #
    #     if global_estimate:
    #         try:
    #             from cohort.tasks import get_count_task
    #             get_count_task.delay(conf.get_fhir_authorization_header(self.context.get("request")),
    #                                  conf.format_json_request(str(rqs.serialized_query)),
    #                                  res_dm_global.uuid)
    #         except Exception as e:
    #             result_cr.dated_measure_global.request_job_fail_msg = f"ERROR: Could not launch FHIR cohort count: {e}"
    #             result_cr.dated_measure_global.request_job_status = JobStatus.failed
    #             result_cr.dated_measure_global.save()
    #
    #     if not validated_data.get("fhir_group_id"):
    #         try:
    #             from cohort.tasks import create_cohort_task
    #             create_cohort_task.delay(conf.get_fhir_authorization_header(self.context.get("request")),
    #                                      conf.format_json_request(str(rqs.serialized_query)),
    #                                      result_cr.uuid)
    #         except Exception as e:
    #             result_cr.delete()
    #             raise ValidationError(f"INTERNAL ERROR: Could not launch FHIR cohort creation: {e}")
    #     return result_cr


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
                raise ValidationError("You cannot provide a request_id that is not the same as the id of the request "
                                      "bound to the previous_snapshot")
            validated_data["request"] = previous_snapshot.request
        elif request:
            if len(request.query_snapshots.all()) != 0:
                raise ValidationError("You have to provide a previous_snapshot_id if the request is not empty of "
                                      "query snaphots")
        else:
            raise ValidationError("You have to provide a previous_snapshot_id or a request_id if the request has not "
                                  "query snapshots bound to it yet")

        serialized_query = validated_data.get("serialized_query")
        try:
            json.loads(serialized_query)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Serialized_query could not be recognized as json: {e.msg}")

        # post_validate_cohort is called this way
        # so that fhir_api can be mocked in tests
        validate_resp = conf.post_validate_cohort(conf.format_json_request(serialized_query),
                                                  conf.get_fhir_authorization_header(self.context.get("request")))
        if not validate_resp.success:
            raise ValidationError(f"Serialized_query, after formatting, is not accepted by "
                                  "FHIR server: {validate_resp.err_msg}")

        validated_data["perimeters_ids"] = conf.retrieve_perimeters(serialized_query)

        res = super(RequestQuerySnapshotSerializer, self).create(validated_data=validated_data)

        if res.previous_snapshot is not None:
            for rqs in res.previous_snapshot.next_snapshots.all():
                rqs.is_active_branch = False
                rqs.save()

        return res

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

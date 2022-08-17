import json

from rest_framework import serializers
from cohort.models import User
from admin_cohort.serializers import BaseSerializer, OpenUserSerializer
import cohort.conf_cohort_job_api as fhir_api
from cohort.FhirAPi import JobStatus
from cohort.conf_cohort_job_api import get_fhir_authorization_header, \
    format_json_request, retrieve_perimeters
from cohort.models import Request, CohortResult, RequestQuerySnapshot, \
    DatedMeasure, Folder, GLOBAL_DM_MODE


class PrimaryKeyRelatedFieldWithOwner(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context.get("request", None).user
        if user is None:
            raise Exception(
                "Internal error: No context request provided to serializer")
        qs = super(PrimaryKeyRelatedFieldWithOwner, self).get_queryset()
        return qs.filter(owner=user)


class UserPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context.get("request", None).user
        if user is None:
            raise Exception(
                "Internal error: No context request provided to serializer")
        qs = super(UserPrimaryKeyRelatedField, self).get_queryset()
        return qs.filter(provider_username=user.provider_username)


class DatedMeasureSerializer(BaseSerializer):
    request = serializers.UUIDField(read_only=True, required=False,
                                    source='request_id')

    class Meta:
        model = DatedMeasure
        fields = "__all__"
        optional = []
        read_only_fields = [
            "count_task_id",
            "request_job_id",
            "request_job_status",
            "request_job_fail_msg",
            "request_job_duration",
            "mode",
            "request",
        ]

    def update(self, instance, validated_data):
        for f in ['owner', 'request_query_snapshot']:
            if f in validated_data:
                raise serializers.ValidationError(
                    f'{f} field cannot bu updated manually'
                )
        return super(DatedMeasureSerializer, self).update(
            instance, validated_data
        )

    def partial_update(self, instance, validated_data):
        for f in ['owner', 'request', 'request_query_snapshot']:
            if f in validated_data:
                raise serializers.ValidationError(
                    f'{f} field cannot bu updated manually'
                )
        return super(DatedMeasureSerializer, self).partial_update(
            instance, validated_data
        )

    def create(self, validated_data):
        rqs = validated_data.get("request_query_snapshot", None)
        measure = validated_data.get("measure", None)
        fhir_datetime = validated_data.get("fhir_datetime", None)

        if rqs is None:
            raise serializers.ValidationError(
                "You have to provide a request_query_snapshot_id to bind "
                "the dated measure to it"
            )

        if (measure is not None and fhir_datetime is None) \
                or (measure is None and fhir_datetime is not None):
            raise serializers.ValidationError(
                "If you provide measure or fhir_datetime, you have to "
                "provide the other"
            )

        res_dm = super(DatedMeasureSerializer, self).create(
            validated_data=validated_data
        )

        if measure is None:
            try:
                from cohort.tasks import get_count_task
                get_count_task(
                    get_fhir_authorization_header(
                        self.context.get("request", None)
                    ),
                    format_json_request(str(rqs.serialized_query)),
                    res_dm.uuid
                )
            except Exception as e:
                res_dm.delete()
                raise serializers.ValidationError(
                    f"INTERNAL ERROR: Could not launch FHIR cohort count: {e}")

        return res_dm


class CohortResultSerializer(BaseSerializer):
    result_size = serializers.IntegerField(read_only=True)
    request = serializers.UUIDField(read_only=True, required=False,
                                    source='request_id')
    request_query_snapshot = PrimaryKeyRelatedFieldWithOwner(
        queryset=RequestQuerySnapshot.objects.all()
    )
    dated_measure = PrimaryKeyRelatedFieldWithOwner(
        queryset=DatedMeasure.objects.all(), required=False
    )
    dated_measure_global = PrimaryKeyRelatedFieldWithOwner(
        queryset=DatedMeasure.objects.all(), required=False
    )
    # request_query_snapshot = serializers.UUIDField(
    #     read_only=True, required=False, source='request_query_snapshot_id')
    # dated_measure = DatedMeasureSerializer()
    # dated_measure_global = DatedMeasureSerializer(required=False)

    global_estimate = serializers.BooleanField(
        write_only=True, allow_null=True, default=True
    )

    fhir_group_id = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )

    class Meta:
        model = CohortResult
        fields = "__all__"
        # exclude = ["request_query_snapshot", "request"]
        # write_only_fields = ["dated_measure_id"]
        read_only_fields = [
            "create_task_id",
            "request_job_id",
            "request_job_status",
            "request_job_fail_msg",
            "request_job_duration",

            # "request_query_snapshot",
            # "request"
        ]

    def update(self, instance, validated_data):
        for f in [
            'owner', 'request', 'request_query_snapshot', 'dated_measure',
            'dated_measure_id', 'type', 'owner_id', 'request_id',
            'request_query_snapshot_id'
        ]:
            if f in validated_data:
                raise serializers.ValidationError(
                    f'{f} field cannot be updated manually')
        return super(CohortResultSerializer, self) \
            .update(instance, validated_data)

    def partial_update(self, instance, validated_data):
        for f in ['owner', 'request', 'request_query_snapshot',
                  'dated_measure', 'type']:
            if f in validated_data:
                raise serializers.ValidationError(
                    f'{f} field cannot be updated manually')
        return super(CohortResultSerializer, self) \
            .partial_update(instance, validated_data)

    def create(self, validated_data):
        if validated_data.get("type", None) is not None:
            raise serializers.ValidationError("You cannot provide a type")

        rqs = validated_data.get("request_query_snapshot", None)
        global_estimate = validated_data.pop("global_estimate", None)

        if rqs is None:
            raise serializers.ValidationError(
                "You have to provide a request_query_snapshot_id to bind "
                "the cohort result to it"
            )

        dm = validated_data.get(
            "dated_measure", dict(fhir_datetime=None, measure=None)
        )
        if not isinstance(dm, DatedMeasure):
            if "measure" in dm and dm["measure"] is None:
                dm = DatedMeasure.objects.create(
                    owner=rqs.owner,
                    request_query_snapshot=rqs,
                )
                dm.save()
            else:
                dm_serializer = DatedMeasureSerializer(
                    data={
                        **dm,
                        "owner": rqs.owner.provider_username,
                        "request_query_snapshot": rqs.uuid
                    }, context=self.context)

                dm_serializer.is_valid(raise_exception=True)
                dm = dm_serializer.save()
            validated_data["dated_measure"] = dm

        res_dm_global: DatedMeasure = None
        if global_estimate:
            res_dm_global: DatedMeasure = DatedMeasure.objects.create(
                owner=rqs.owner,
                request_query_snapshot=rqs,
                mode=GLOBAL_DM_MODE
            )
            validated_data["dated_measure_global"] = res_dm_global

        result_cr: CohortResult = super(CohortResultSerializer, self) \
            .create(validated_data=validated_data)

        if global_estimate:
            try:
                from cohort.tasks import get_count_task
                get_count_task.delay(
                    get_fhir_authorization_header(
                        self.context.get("request", None)
                    ),
                    format_json_request(str(rqs.serialized_query)),
                    res_dm_global.uuid
                )
            except Exception as e:
                result_cr.dated_measure_global.request_job_fail_msg \
                    = f"INTERNAL ERROR: Could not launch FHIR cohort count: {e}"
                result_cr.dated_measure_global \
                    .request_job_status = JobStatus.ERROR.value
                result_cr.dated_measure_global.save()

        # once it has been created, we launch Fhir API cohort creation
        # task to complete it, if fhir_group_id was not already provided
        if validated_data.get("fhir_group_id", None) is None:
            try:
                from cohort.tasks import create_cohort_task
                create_cohort_task.delay(
                    get_fhir_authorization_header(
                        self.context.get("request", None)
                    ),
                    format_json_request(str(rqs.serialized_query)),
                    result_cr.uuid
                )

            except Exception as e:
                result_cr.delete()
                raise serializers.ValidationError(
                    f"INTERNAL ERROR: Could not launch "
                    f"FHIR cohort creation: {e}"
                )

        return result_cr


class CohortResultSerializerFullDatedMeasure(CohortResultSerializer):
    dated_measure = DatedMeasureSerializer(required=False, allow_null=True)
    dated_measure_global = DatedMeasureSerializer(
        required=False, allow_null=True
    )


class ReducedRequestQuerySnapshotSerializer(BaseSerializer):
    class Meta:
        model = RequestQuerySnapshot
        fields = "__all__"


class RequestQuerySnapshotSerializer(BaseSerializer):
    request = PrimaryKeyRelatedFieldWithOwner(
        queryset=Request.objects.all(), required=False)
    previous_snapshot = PrimaryKeyRelatedFieldWithOwner(
        required=False, queryset=RequestQuerySnapshot.objects.all())
    # request = serializers.UUIDField(
    #     required=False, source='request')
    # previous_snapshot = serializers.UUIDField(
    #     required=False, source='previous_snapshot_id')

    dated_measures = DatedMeasureSerializer(many=True, read_only=True)
    cohort_results = CohortResultSerializer(many=True, read_only=True)
    shared_by = OpenUserSerializer(
        allow_null=True, read_only=True, source='shared_by.provider')

    class Meta:
        model = RequestQuerySnapshot
        fields = "__all__"
        optional_fields = ["previous_snapshot", "request"]
        # exclude = ["request", "owner"]
        read_only_fields = ["is_active_branch", "care_sites_ids",
                            # "request", "owner",
                            "dated_measures", "cohort_results", 'shared_by',
                            ]

    def create(self, validated_data):
        previous_snapshot = validated_data.get("previous_snapshot", None)
        request = validated_data.get("request", None)
        if previous_snapshot is not None:
            for rqs in previous_snapshot.next_snapshots.all():
                rqs.active = False
                rqs.save()
            if request is not None \
                    and request.uuid != previous_snapshot.request.uuid:
                raise serializers.ValidationError(
                    "You cannot provide a request_id that is not the same as "
                    "the id of the request bound to the previous_snapshot")
            validated_data["request_id"] = previous_snapshot.request.uuid
        elif request is not None:
            if len(request.query_snapshots.all()) != 0:
                raise serializers.ValidationError(
                    "You have to provide a previous_snapshot_id if the "
                    "request is not empty of query snaphots")
        else:
            raise serializers.ValidationError(
                "You have to provide a previous_snapshot_id or a request_id "
                "if the request has not query snapshots bound to it yet")

        serialized_query = validated_data.get("serialized_query", None)
        if serialized_query is None:
            raise serializers.ValidationError(
                "You have to provide a serialized_query")

        try:
            json.loads(serialized_query)
        except json.JSONDecodeError as e:
            raise serializers.ValidationError(
                f"Serialized_query could not be recognized as json: {e.msg}")

        # post_validate_cohort is called this way
        # so that fhir_api can be mocked in tests
        validate_resp = fhir_api.post_validate_cohort(
            format_json_request(serialized_query),
            get_fhir_authorization_header(self.context.get("request"))
        )
        if not validate_resp.success:
            raise serializers.ValidationError(
                f"Serialized_query, after formatting, is not accepted by "
                f"FHIR server: {validate_resp.err_msg}")

        validated_data["perimeters_ids"] = retrieve_perimeters(serialized_query)

        return super(RequestQuerySnapshotSerializer, self) \
            .create(validated_data=validated_data)

    def update(self, instance, validated_data):
        for f in ['owner', 'request', 'owner_id', 'request_id']:
            if f in validated_data:
                raise serializers.ValidationError(
                    f'{f} field cannot be updated manually')
        return super(RequestQuerySnapshotSerializer, self) \
            .update(instance, validated_data)

    def partial_update(self, instance, validated_data):
        for f in ['owner', 'request', 'owner_id', 'request_id']:
            if f in validated_data:
                raise serializers.ValidationError(
                    f'{f} field cannot be updated manually')
        return super(RequestQuerySnapshotSerializer, self) \
            .partial_update(instance, validated_data)


class RequestSerializer(BaseSerializer):
    # owner_id = UserPrimaryKeyRelatedField(source='owner',
    # queryset=User.objects.all(), required=False)
    # parent_folder_id = PrimaryKeyRelatedFieldWithOwner(source='parent_folder',
    # queryset=Folder.objects.all(), required=False)
    # query_snapshots = RequestQuerySnapshotSerializer(many=True,
    # read_only=True)
    query_snapshots = serializers.SlugRelatedField(slug_field='uuid', many=True,
                                                   read_only=True)
    shared_by = OpenUserSerializer(read_only=True)

    class Meta:
        model = Request
        fields = "__all__"
        # exclude = ["owner"]
        read_only_fields = [
            # "owner",
            "query_snapshots",
            'shared_by',
        ]

    def update(self, instance, validated_data):
        for f in ['owner']:
            if f in validated_data:
                raise serializers.ValidationError(
                    f'{f} field cannot bu updated manually')
        return super(RequestSerializer, self).update(instance, validated_data)

    def partial_update(self, instance, validated_data):
        for f in ['owner']:
            if f in validated_data:
                raise serializers.ValidationError(
                    f'{f} field cannot bu updated manually')
        return super(RequestSerializer, self) \
            .partial_update(instance, validated_data)


class ReducedFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = "__all__"
        # exclude = ["owner"]
        read_only_fields = ["owner"]


class FolderSerializer(BaseSerializer):
    parent_folder_id = PrimaryKeyRelatedFieldWithOwner(
        source='parent_folder', queryset=Folder.objects.all(), required=False)
    owner_id = UserPrimaryKeyRelatedField(
        source='owner', queryset=User.objects.all(), required=False)

    children_folders = ReducedFolderSerializer(many=True, read_only=True)
    # requests = RequestSerializer(many=True, read_only=True)
    requests = serializers.SlugRelatedField(slug_field='uuid', many=True,
                                            read_only=True)

    class Meta:
        model = Folder
        fields = "__all__"
        # exclude = ["owner"]
        read_only_fields = ["owner",
                            "children_folders", "requests"
                            ]

    def update(self, instance, validated_data):
        for f in ['owner']:
            if f in validated_data:
                raise serializers.ValidationError(
                    f'{f} field cannot bu updated manually')
        return super(FolderSerializer, self).update(instance, validated_data)

    def partial_update(self, instance, validated_data):
        for f in ['owner']:
            if f in validated_data:
                raise serializers.ValidationError(
                    f'{f} field cannot bu updated manually')
        return super(FolderSerializer, self) \
            .partial_update(instance, validated_data)

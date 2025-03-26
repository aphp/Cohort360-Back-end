from enum import StrEnum
from typing import Union, Optional, List

from rest_framework import serializers

from admin_cohort.models import User
from admin_cohort.services.ws_event_manager import WebSocketMessage
from admin_cohort.types import JobStatus
from admin_cohort.exceptions import MissingDataError
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


class FolderSerializer(serializers.ModelSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=True, write_only=True)
    requests_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ["uuid",
                  "name",
                  "description",
                  "owner",
                  "created_at",
                  "requests_count"
                  ]
        read_only_fields = ["uuid",
                            "created_at"
                            ]

    def get_requests_count(self, obj) -> int:
        return obj.requests.count()


class FolderCreateSerializer(serializers.ModelSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=True)

    class Meta:
        model = Folder
        fields = ["name",
                  "owner",
                  "description"
                  ]


class FolderPatchSerializer(serializers.ModelSerializer):

    class Meta:
        model = Folder
        fields = ["name",
                  "description"
                  ]


class DatedMeasureCreateSerializer(serializers.ModelSerializer):
    request = PrimaryKeyRelatedFieldWithOwner(required=True, queryset=Request.objects.all())
    request_query_snapshot = PrimaryKeyRelatedFieldWithOwner(required=True, queryset=RequestQuerySnapshot.objects.all())

    class Meta:
        model = DatedMeasure
        fields = ["request",
                  "request_query_snapshot"]


class DatedMeasurePatchSerializer(serializers.ModelSerializer):
    request_job_status = serializers.CharField(required=False)
    message = serializers.CharField(required=False)
    group_count = serializers.CharField(required=False)
    minimum = serializers.CharField(required=False)
    maximum = serializers.CharField(required=False)

    class Meta:
        model = DatedMeasure
        fields = ["request_job_status",
                  "group_count",
                  "message",
                  "minimum",
                  "maximum"]

    def to_internal_value(self, data):
        if "group_count" in data:
            data["group.count"] = data.pop("group_count")
        return super().to_internal_value(data)


class DatedMeasureSerializer(serializers.ModelSerializer):
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


class SampledCohortResultSerializer(serializers.ModelSerializer):

    class Meta:
        model = CohortResult
        fields = ["uuid",
                  "name",
                  "sampling_ratio"]


class SampledCohortResultCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    parent_cohort = PrimaryKeyRelatedFieldWithOwner(required=True, queryset=CohortResult.objects.filter(parent_cohort__isnull=True))
    sampling_ratio = serializers.FloatField(required=True)

    class Meta:
        model = CohortResult
        fields = ["name",
                  "description",
                  "owner",
                  "parent_cohort",
                  "sampling_ratio"]


class CohortResultSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    request_query_snapshot = PrimaryKeyRelatedFieldWithOwner(queryset=RequestQuerySnapshot.objects.all(), required=False)
    dated_measure = PrimaryKeyRelatedFieldWithOwner(queryset=DatedMeasure.objects.all(), required=False, write_only=True)
    parent_cohort = PrimaryKeyRelatedFieldWithOwner(queryset=CohortResult.objects.filter(parent_cohort__isnull=True), required=False)
    sampling_ratio = serializers.FloatField(required=False)
    sample_cohorts = SampledCohortResultSerializer(many=True, read_only=True)
    result_size = serializers.IntegerField(required=False)
    measure_min = serializers.IntegerField(required=False)
    measure_max = serializers.IntegerField(required=False)
    exportable = serializers.BooleanField(required=False)
    group_id = serializers.CharField(required=False)
    request_job_status = serializers.CharField(required=False)
    request_job_fail_msg = serializers.CharField(required=False)
    favorite = serializers.BooleanField(required=False)
    request = serializers.SerializerMethodField()

    class Meta:
        model = CohortResult
        fields = ["uuid",
                  "name",
                  "owner",
                  "request_query_snapshot",
                  "dated_measure",
                  "parent_cohort",
                  "sampling_ratio",
                  "sample_cohorts",
                  "result_size",
                  "measure_min",
                  "measure_max",
                  "group_id",
                  "request_job_status",
                  "request_job_fail_msg",
                  "exportable",
                  "created_at",
                  "modified_at",
                  "description",
                  "favorite",
                  "request",
                  ]

    def get_request(self, obj) -> dict:
        return {'uuid': obj.request_query_snapshot.request_id,
                'name': obj.request_query_snapshot.request.name,
                'description': obj.request_query_snapshot.request.description
                }

    def validate_sampling_ratio(self, value):
        if value is not None and not 0 < value < 1:
            raise serializers.ValidationError("Sampling ratio must be between 0 and 1")
        return value

    def create(self, validated_data):
        parent_cohort = validated_data.get("parent_cohort")
        if parent_cohort is not None:
            # complete data to create sampled cohort
            new_dm = DatedMeasure.objects.create(owner=parent_cohort.owner,
                                                 request_query_snapshot=parent_cohort.request_query_snapshot
                                                 )
            validated_data.update({"request_query_snapshot": parent_cohort.request_query_snapshot,
                                   "dated_measure": new_dm
                                   })
        return super().create(validated_data)

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res.update({"parent_cohort": instance.parent_cohort and
                                     {"uuid": instance.parent_cohort.uuid,
                                      "name": instance.parent_cohort.name
                                      }
                                     or None
                    })
        return res


class CohortResultCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    description = serializers.CharField(allow_blank=True, allow_null=True)
    owner = UserPrimaryKeyRelatedField(required=True, queryset=User.objects.all())
    request_query_snapshot = PrimaryKeyRelatedFieldWithOwner(required=True, queryset=RequestQuerySnapshot.objects.all())
    dated_measure = PrimaryKeyRelatedFieldWithOwner(required=True, queryset=DatedMeasure.objects.all())

    class Meta:
        model = CohortResult
        fields = ["name",
                  "description",
                  "owner",
                  "request_query_snapshot",
                  "dated_measure"]


class CohortResultPatchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    favorite = serializers.BooleanField(required=False)
    request_job_status = serializers.CharField(required=False)
    request_job_fail_msg = serializers.CharField(required=False)
    group_id = serializers.CharField(required=False)

    class Meta:
        model = CohortResult
        fields = ["name",
                  "description",
                  "favorite",
                  "request_job_status",
                  "group_id",
                  "request_job_fail_msg"
                  ]


class CohortRightsSerializer(serializers.Serializer):
    cohort_id = serializers.CharField(allow_null=False)
    rights = serializers.DictField(allow_null=True)


class RQSReducedSerializer(serializers.ModelSerializer):
    cohorts_count = serializers.SerializerMethodField()
    patients_count = serializers.SerializerMethodField()

    class Meta:
        model = RequestQuerySnapshot
        fields = ["uuid",
                  "name",
                  "created_at",
                  "cohorts_count",
                  "patients_count",
                  "version"]

    def get_cohorts_count(self, obj) -> int:
        return obj.cohort_results.count()

    def get_patients_count(self, obj) -> int | str:
        dms_with_normal_cohorts = obj.dated_measures.filter(cohorts__parent_cohort__isnull=True)
        if dms_with_normal_cohorts.exists():
            latest_dm = dms_with_normal_cohorts.latest("created_at")
            return latest_dm.measure if latest_dm.measure is not None else "NA"
        return "NA"


class RQSSerializer(serializers.ModelSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    request = PrimaryKeyRelatedFieldWithOwner(queryset=Request.objects.all(), required=False)
    previous_snapshot = PrimaryKeyRelatedFieldWithOwner(queryset=RequestQuerySnapshot.objects.all(), required=False)
    dated_measures = serializers.SerializerMethodField()
    cohort_results = CohortResultSerializer(many=True, read_only=True)

    class Meta:
        model = RequestQuerySnapshot
        fields = ["uuid",
                  "owner",
                  "name",
                  "version",
                  "created_at",
                  "modified_at",
                  "request",
                  "previous_snapshot",
                  "serialized_query",
                  "perimeters_ids",
                  "dated_measures",
                  "cohort_results",
                  ]

    def get_dated_measures(self, obj) -> List[dict]:
        dms_with_normal_cohorts = obj.dated_measures.filter(cohorts__parent_cohort__isnull=True) \
                                                    .order_by('-created_at')
        return DatedMeasureSerializer(dms_with_normal_cohorts, many=True).data


class RQSCreateSerializer(serializers.ModelSerializer):
    request = PrimaryKeyRelatedFieldWithOwner(required=False, queryset=Request.objects.all())
    previous_snapshot = PrimaryKeyRelatedFieldWithOwner(required=False, queryset=RequestQuerySnapshot.objects.all())
    owner = UserPrimaryKeyRelatedField(required=True, queryset=User.objects.all())

    class Meta:
        model = RequestQuerySnapshot
        fields = ["request",
                  "previous_snapshot",
                  "serialized_query",
                  "owner"
                  ]


class RQSShareSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    recipients = serializers.CharField(required=True)
    notify_by_email = serializers.BooleanField(required=False)

    class Meta:
        model = RequestQuerySnapshot
        fields = ["name",
                  "recipients",
                  "notify_by_email"]


class RequestSerializer(serializers.ModelSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=True, write_only=True)
    parent_folder = PrimaryKeyRelatedFieldWithOwner(queryset=Folder.objects.all(), required=True)
    query_snapshots = RQSReducedSerializer(many=True, read_only=True)
    shared_by = serializers.SerializerMethodField()
    updated_at = serializers.CharField(read_only=True)

    class Meta:
        model = Request
        fields = ["uuid",
                  "name",
                  "description",
                  "favorite",
                  "owner",
                  "query_snapshots",
                  "shared_by",
                  "parent_folder",
                  "updated_at",
                  ]

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res.update({"query_snapshots": sorted(res["query_snapshots"], key=lambda rqs: rqs["created_at"], reverse=True),
                    "parent_folder": {"uuid": instance.parent_folder.uuid,
                                      "name": instance.parent_folder.name,
                                      "description": instance.parent_folder.description,
                                      }
                    })
        return res

    def get_shared_by(self, obj) -> Optional[str]:
        return obj.shared_by and obj.shared_by.display_name or None


class RequestCreateSerializer(serializers.ModelSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all())
    parent_folder = PrimaryKeyRelatedFieldWithOwner(required=False, queryset=Folder.objects.all())

    class Meta:
        model = Request
        fields = ["name",
                  "description",
                  "favorite",
                  "owner",
                  "parent_folder"]


class RequestPatchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    parent_folder = PrimaryKeyRelatedFieldWithOwner(required=False, queryset=Folder.objects.all())

    class Meta:
        model = Request
        fields = ["name",
                  "description",
                  "favorite",
                  "parent_folder"]


class FhirFilterSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = FhirFilter
        fields = '__all__'

    def create(self, validated_data):
        validated_data["owner"] = self.context.get('request').user
        return super().create(validated_data)


class FhirFilterCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = FhirFilter
        fields = ["fhir_resource",
                  "fhir_version",
                  "filter",
                  "name"]


class FhirFilterPatchSerializer(FhirFilterCreateSerializer):
    ...


class FeasibilityStudySerializer(serializers.ModelSerializer):
    owner = UserPrimaryKeyRelatedField(queryset=User.objects.all(), required=False)

    class Meta:
        model = FeasibilityStudy
        fields = ["uuid",
                  "owner",
                  "created_at",
                  "request_job_status",
                  "total_count",
                  "request_query_snapshot"]


class FeasibilityStudyCreateSerializer(serializers.ModelSerializer):
    request_query_snapshot = PrimaryKeyRelatedFieldWithOwner(queryset=RequestQuerySnapshot.objects.all())

    class Meta:
        model = FeasibilityStudy
        fields = ["request_query_snapshot"]



class FeasibilityStudyPatchSerializer(DatedMeasurePatchSerializer):
    extra = serializers.DictField(required=True)

    class Meta:
        model = FeasibilityStudy
        fields = ["request_job_status",
                  "group_count",
                  "message",
                  "extra"]

    def to_internal_value(self, data):
        if "group_count" in data:
            data["group.count"] = data.pop("group_count")
        return super().to_internal_value(data)


class RequestRefreshScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestRefreshSchedule
        fields = '__all__'
        read_only_fields = ["last_refresh",
                            "last_refresh_succeeded",
                            "last_refresh_count",
                            "last_refresh_error_msg"]


class JobName(StrEnum):
    COUNT = 'count'
    CREATE = 'create'


class WSJobStatus(WebSocketMessage):
    status: Union[JobStatus, str]
    uuid: str
    job_name: JobName
    extra_info: dict


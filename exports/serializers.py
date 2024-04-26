
from rest_framework import serializers

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from workspaces.models import Account
from exports.models import ExportRequest, ExportRequestTable, Datalab, InfrastructureProvider, ExportTable, ExportResultStat, Export


class ExportRequestTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportRequestTable
        fields = "__all__"
        read_only_fields = ["export_request_table_id",
                            "target_table_name",
                            "source_table_name",
                            "export_request",
                            "deleted_at"]


class ExportRequestListSerializer(serializers.ModelSerializer):
    owner = serializers.SlugRelatedField(read_only=True, slug_field="display_name")
    cohort_name = serializers.CharField(read_only=True)
    patients_count = serializers.IntegerField(read_only=True)
    target_env = serializers.CharField(read_only=True)

    class Meta:
        model = ExportRequest
        fields = ("owner",
                  "output_format",
                  "cohort_id",
                  "cohort_name",
                  "patients_count",
                  "insert_datetime",
                  "request_job_status",
                  "target_env",
                  "target_name")


class ExportRequestSerializer(serializers.ModelSerializer):
    tables = ExportRequestTableSerializer(many=True, write_only=True, required=False)
    cohort = serializers.PrimaryKeyRelatedField(queryset=CohortResult.objects.filter(request_job_status=JobStatus.finished),
                                                source='cohort_fk')
    cohort_id = serializers.IntegerField(required=False)

    class Meta:
        model = ExportRequest
        fields = "__all__"
        read_only_fields = ["execution_request_datetime",
                            "is_user_notified",
                            "cleaned_at",
                            "insert_datetime",
                            "update_datetime",
                            "delete_datetime",
                            "request_job_id",
                            "request_job_status",
                            "request_job_fail_msg",
                            "request_job_duration",
                            "review_request_datetime",
                            "reviewer_fk"
                            ]
        extra_kwargs = {'cohort': {'required': True},
                        'output_format': {'required': True},
                        'owner': {'required': True}
                        }


class OwnedCohortPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get('request')
        queryset = super(OwnedCohortPrimaryKeyRelatedField, self).get_queryset()
        if not request or not queryset:
            return None
        return queryset.filter(owner=request.user)


class ExportRequestSerializerNoReviewer(ExportRequestSerializer):
    cohort = OwnedCohortPrimaryKeyRelatedField(queryset=CohortResult.objects.all(), source='cohort_fk')


class AnnexeAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ('uid', 'username', 'name', 'firstname', 'lastname', 'gid')
        read_only_fields = ('uid', 'username', 'name', 'firstname', 'lastname', 'gid')


class AnnexeCohortResultSerializer(serializers.ModelSerializer):
    dated_measure = serializers.SlugRelatedField(read_only=True, slug_field='measure')

    class Meta:
        model = CohortResult
        fields = ('uuid', 'owner', 'name', 'description', 'dated_measure',
                  'created_at', 'request_job_status', 'fhir_group_id')
        read_only_fields = ('owner', 'name', 'description', 'dated_measure',
                            'created_at', 'request_job_status', 'fhir_group_id')


class DatalabSerializer(serializers.ModelSerializer):

    class Meta:
        model = Datalab
        fields = "__all__"


class InfrastructureProviderSerializer(serializers.ModelSerializer):

    class Meta:
        model = InfrastructureProvider
        fields = "__all__"


class ExportResultStatSerializer(serializers.ModelSerializer):
    export_name = serializers.SlugRelatedField(read_only=True, slug_field='name')

    class Meta:
        model = ExportResultStat
        fields = "__all__"


class ExportTableSerializer(serializers.ModelSerializer):

    class Meta:
        model = ExportTable
        fields = ["name",
                  "respect_table_relationships",
                  "fhir_filter",
                  "cohort_result_source"]


class ExportSerializer(serializers.ModelSerializer):
    export_tables = ExportTableSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Export
        fields = ["uuid",
                  "output_format",
                  "datalab",
                  "nominative",
                  "shift_dates",
                  "export_tables",
                  "motivation",
                  "owner",
                  "target_name",
                  "target_location",
                  "request_job_id",
                  "request_job_status",
                  "request_job_fail_msg"]
        read_only_fields = ["uuid",
                            "request_job_id",
                            "request_job_status",
                            "request_job_fail_msg"]
        extra_kwargs = {'owner': {'required': False},
                        'motivation': {'required': False}}

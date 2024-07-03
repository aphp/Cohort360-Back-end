
from rest_framework import serializers

from cohort.models import CohortResult
from exports.models import Datalab, InfrastructureProvider, ExportTable, ExportResultStat, Export


class ExportsListSerializer(serializers.ModelSerializer):
    owner = serializers.SlugRelatedField(read_only=True, slug_field="display_name")
    cohort_id = serializers.CharField(read_only=True)
    cohort_name = serializers.CharField(read_only=True)
    patients_count = serializers.IntegerField(read_only=True)
    target_datalab = serializers.CharField(read_only=True)

    class Meta:
        model = Export
        fields = ("owner",
                  "output_format",  # todo: /!\ split pages in Portail for CSV/Hive exports
                  "cohort_id",
                  "cohort_name",
                  "patients_count",
                  "created_at",     # todo:  was: `insert_datetime`
                  "request_job_status",
                  "target_datalab",
                  "target_name")


class AnnexeCohortResultSerializer(serializers.ModelSerializer):
    dated_measure = serializers.SlugRelatedField(read_only=True, slug_field='measure')

    class Meta:
        model = CohortResult
        fields = ('uuid', 'owner', 'name', 'description', 'dated_measure',
                  'created_at', 'request_job_status', 'group_id')
        read_only_fields = ('owner', 'name', 'description', 'dated_measure',
                            'created_at', 'request_job_status', 'group_id')


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
                  "group_tables",
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

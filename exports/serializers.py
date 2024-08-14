
from rest_framework import serializers

from cohort.models import CohortResult
from exports.models import Datalab, InfrastructureProvider, ExportTable, ExportResultStat, Export


class ExportsCohortResultSerializer(serializers.ModelSerializer):

    class Meta:
        model = CohortResult
        fields = ['uuid', 'owner', 'name']


class DatalabSerializer(serializers.ModelSerializer):
    class Meta:
        model = Datalab
        exclude = ["created_at", "modified_at", "deleted", "deleted_by_cascade"]


class InfrastructureProviderSerializer(serializers.ModelSerializer):

    class Meta:
        model = InfrastructureProvider
        fields = "__all__"


class ExportResultStatSerializer(serializers.ModelSerializer):
    export_target = serializers.CharField(read_only=True, source='export.target_name')

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
    export_tables = ExportTableSerializer(many=True, required=False)

    class Meta:
        model = Export
        read_only_fields = ["uuid",
                            "target_name",
                            "target_location",
                            "request_job_id",
                            "request_job_status",
                            "request_job_fail_msg"]
        fields = read_only_fields + ["owner",
                                     "output_format",
                                     "datalab",
                                     "nominative",
                                     "shift_dates",
                                     "group_tables",
                                     "export_tables",
                                     "motivation"]
        extra_kwargs = {'motivation': {'required': False}}


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

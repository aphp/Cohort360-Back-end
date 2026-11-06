from rest_framework import serializers

from cohort.models import CohortResult
from exports.enums import ExportPurpose
from exports.models import Datalab, InfrastructureProvider, ExportTable, ExportResultStat, Export, ExportProjectDetails


class ExportsCohortResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CohortResult
        fields = ["uuid", "owner", "name"]


class InfrastructureProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfrastructureProvider
        exclude = ["created_at", "modified_at", "deleted", "deleted_by_cascade"]


class DatalabSerializer(serializers.ModelSerializer):
    infrastructure_provider = serializers.PrimaryKeyRelatedField(queryset=InfrastructureProvider.objects.all())

    class Meta:
        model = Datalab
        exclude = ["modified_at", "deleted", "deleted_by_cascade"]

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res["infrastructure_provider"] = {"uuid": instance.infrastructure_provider_id, "name": instance.infrastructure_provider.name}
        return res


class ExportResultStatSerializer(serializers.ModelSerializer):
    export_target = serializers.CharField(read_only=True, source="export.target_name")

    class Meta:
        model = ExportResultStat
        fields = "__all__"


class ExportTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportTable
        fields = [
            "name",
            "respect_table_relationships",
            "fhir_filter",
            "cohort_result_source",
            "pivot_merge",
            "pivot_merge_columns",
            "pivot_merge_ids",
        ]


class ExportProjectDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportProjectDetails
        fields = ["title", "project_leader", "start_date", "end_date"]

    def validate(self, attrs):
        start_date, end_date = attrs.get("start_date"), attrs.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("The end date must not be earlier than the start date")
        return attrs


class ExportSerializer(serializers.ModelSerializer):
    export_tables = ExportTableSerializer(many=True, required=False)
    project_details = ExportProjectDetailsSerializer(required=False, allow_null=True)

    class Meta:
        model = Export
        read_only_fields = ["uuid", "request_job_id", "request_job_status", "request_job_fail_msg"]
        fields = read_only_fields + [
            "owner",
            "output_format",
            "datalab",
            "nominative",
            "target_name",
            "target_location",
            "shift_dates",
            "group_tables",
            "export_tables",
            "motivation",
            "purpose",
            "project_details",
        ]

    def validate(self, attrs):
        is_internal_research = attrs.get("purpose") == ExportPurpose.INTERNAL_RESEARCH.value
        has_details = attrs.get("project_details") is not None
        if is_internal_research and not has_details:
            raise serializers.ValidationError("Project details are required for an internal research export")
        if has_details and not is_internal_research:
            raise serializers.ValidationError("Project details are only allowed for an internal research export")
        return attrs

    def create(self, validated_data):
        details = validated_data.pop("project_details", None)
        export = super().create(validated_data)
        if details is not None:
            ExportProjectDetails.objects.create(export=export, **details)
        return export


class ExportPurposePrefillSerializer(serializers.ModelSerializer):
    project_details = ExportProjectDetailsSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Export
        fields = ["purpose", "project_details"]


class ExportTableSerializerCreate(serializers.ModelSerializer):
    table_name = serializers.CharField()
    columns = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = ExportTable
        fields = [
            "table_name",
            "columns",
            "cohort_result_source",
            "fhir_filter",
            "respect_table_relationships",
            "pivot_merge",
            "pivot_merge_columns",
            "pivot_merge_ids",
        ]


class ExportCreateSerializer(serializers.ModelSerializer):
    export_tables = ExportTableSerializerCreate(many=True)
    project_details = ExportProjectDetailsSerializer(required=False, allow_null=True)

    class Meta:
        model = Export
        fields = [
            "motivation",
            "purpose",
            "project_details",
            "output_format",
            "datalab",
            "nominative",
            "shift_dates",
            "group_tables",
            "export_tables",
        ]


class ExportsListSerializer(serializers.ModelSerializer):
    owner = serializers.SlugRelatedField(read_only=True, slug_field="display_name")
    cohort_id = serializers.CharField(read_only=True)
    cohort_name = serializers.CharField(read_only=True)
    patients_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Export
        fields = [
            "uuid",
            "owner",
            "output_format",
            "motivation",
            "cohort_id",
            "cohort_name",
            "patients_count",
            "created_at",
            "modified_at",
            "request_job_status",
            "target_datalab",
            "target_name",
        ]

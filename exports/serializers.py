
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from admin_cohort.types import JobStatus
from admin_cohort.models import User
from cohort.models import CohortResult
from exports.services.rights_checker import rights_checker
from workspaces import conf_workspaces
from workspaces.models import Account
from exports.emails import check_email_address
from exports.models import ExportRequest, ExportRequestTable, Datalab, InfrastructureProvider, ExportTable, ExportResultStat, Export
from exports.types import ExportType


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
    tables = ExportRequestTableSerializer(many=True)
    cohort = serializers.PrimaryKeyRelatedField(queryset=CohortResult.objects.all(), source='cohort_fk')
    reviewer_fk = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)
    cohort_id = serializers.IntegerField(required=False)

    class Meta:
        model = ExportRequest
        fields = "__all__"
        read_only_fields = ["export_request_id",
                            "request_datetime",
                            "execution_request_datetime",
                            "validation_request_datetime",
                            "is_user_notified",
                            "target_location",
                            "target_name",
                            "creator_id",
                            "reviewer_id",
                            "cleaned_at",
                            # Base
                            "insert_datetime",
                            "update_datetime",
                            "delete_datetime",
                            # Job
                            "request_job_id",
                            "request_job_status",
                            "request_job_fail_msg",
                            "request_job_duration",
                            "review_request_datetime",
                            "reviewer_fk"
                            ]
        extra_kwargs = {'cohort': {'required': True},
                        'output_format': {'required': True},
                        'creator': {'required': True},
                        'owner': {'required': True}
                        }

    def create_tables(self, tables, er):
        for table in tables:
            ExportRequestTable.objects.create(export_request=er, **table)

    def create(self, validated_data):
        owner: User = validated_data.get('owner')
        check_email_address(owner.email)
        cohort: CohortResult = validated_data.get('cohort_fk')

        if cohort.request_job_status != JobStatus.finished:
            raise ValidationError('The requested cohort has not finished successfully.')

        validated_data['cohort_id'] = validated_data.get('cohort_fk').fhir_group_id

        output_format = validated_data.get('output_format')
        validated_data['motivation'] = validated_data.get('motivation', "").replace("\n", " -- ")

        rights_checker.check_owner_rights(owner=owner,
                                          output_format=output_format,
                                          nominative=validated_data.get('nominative'),
                                          source_cohorts_ids=[validated_data.get('cohort_fk').uuid])

        if output_format == ExportType.HIVE:
            self.validate_hive_export(validated_data)
        else:
            self.validate_csv_export(validated_data)

        tables = validated_data.pop("tables", [])
        er = super(ExportRequestSerializer, self).create(validated_data)
        self.create_tables(tables, er)
        try:
            from exports.tasks import launch_request
            launch_request.delay(er.id)
        except Exception as e:
            er.request_job_status = JobStatus.failed
            er.request_job_fail_msg = f"INTERNAL ERROR: Could not launch Celery task: {e}"
        return er

    def validate_hive_export(self, validated_data: dict):
        target_unix_account = validated_data.get('target_unix_account')
        if not target_unix_account:
            raise ValidationError("Pour une demande d'export HIVE, il faut fournir target_unix_account")

        owner = validated_data.get('owner')
        validated_data['request_job_status'] = JobStatus.validated
        validated_data['reviewer_fk'] = self.context.get('request').user

        # /!\ Never been used /!\ todo: check with the team if necessary to keep this !
        if not conf_workspaces.is_user_bound_to_unix_account(owner, target_unix_account.aphp_ldap_group_dn):
            raise ValidationError(f"Le compte Unix destinataire ({target_unix_account.pk}) "
                                  f"n'est pas lié à l'utilisateur voulu ({owner.pk})")

    def validate_csv_export(self, validated_data: dict):
        validated_data['request_job_status'] = JobStatus.validated
        creator: User = self.context.get('request').user

        if validated_data.get('owner').pk != creator.pk:
            raise ValidationError("Vous ne pouvez pas effectuer un export CSV pour un autre utilisateur")
        if not validated_data.get('nominative'):
            raise ValidationError("Actuellement, la demande d'export CSV en pseudo-anonymisée n'est pas possible.")
        if validated_data.get('cohort_fk').owner != creator:
            raise ValidationError("Vous ne pouvez pas exporter une cohorte d'un autre utilisateur.")


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
                  "status",
                  "owner",
                  "target_name",
                  "request_job_id",
                  "request_job_status",
                  "request_job_fail_msg"]
        read_only_fields = ["uuid",
                            "request_job_id",
                            "request_job_status",
                            "request_job_fail_msg"]
        extra_kwargs = {'owner': {'required': False},
                        'motivation': {'required': False}}

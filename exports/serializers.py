from typing import List

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

import workspaces.conf_workspaces as conf_workspaces
from accesses.models import DataRight, build_data_rights, Perimeter
from admin_cohort.types import JobStatus
from admin_cohort.models import User
from cohort.models import CohortResult
from exports.services.export import export_service
from workspaces.models import Account
from exports.emails import check_email_address
from exports.models import ExportRequest, ExportRequestTable, Datalab, InfrastructureProvider, ExportTable, ExportResultStat, Export
from exports.permissions import can_review_transfer_jupyter, can_review_export
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


def check_read_rights_on_perimeters(rights: List[DataRight], is_nomi: bool):
    if is_nomi:
        wrong_perims = [r.care_site_id for r in rights if not r.right_read_patient_nominative]
    else:
        wrong_perims = [r.care_site_id for r in rights if not r.right_read_patient_pseudo_anonymised]
    if wrong_perims:
        raise ValidationError(f"L'utilisateur n'a pas le droit de lecture {is_nomi and 'nominative' or 'pseudonymisée'} "
                              f"sur les périmètres: {wrong_perims}.")


def check_csv_export_rights_on_perimeters(rights: List[DataRight], is_nomi: bool):
    if is_nomi:
        wrong_perims = [r.care_site_id for r in rights if not r.right_export_csv_nominative]
    else:
        wrong_perims = [r.care_site_id for r in rights if not r.right_export_csv_pseudo_anonymised]
    if wrong_perims:
        raise ValidationError(f"L'utilisateur n'a pas le droit d'export CSV {is_nomi and 'nominatif' or 'pseudonymisé'} "
                              f"sur les périmètres {wrong_perims}.")


def check_jupyter_export_rights_on_perimeters(rights: List[DataRight], is_nomi: bool):
    if is_nomi:
        wrong_perims = [r.care_site_id for r in rights if not r.right_transfer_jupyter_nominative]
    else:
        wrong_perims = [r.care_site_id for r in rights if not r.right_transfer_jupyter_pseudo_anonymised]
    if wrong_perims:
        raise ValidationError(f"L'utilisateur n'a pas le droit d'export Jupyter {is_nomi and 'nominatif' or 'pseudonymisé'} "
                              f"sur les périmètres {wrong_perims}.")


def check_rights_on_perimeters_for_exports(rights: List[DataRight], export_type: str, is_nomi: bool):
    assert export_type in [e.value for e in ExportType], "Wrong value for `export_type`"
    check_read_rights_on_perimeters(rights=rights, is_nomi=is_nomi)
    if export_type == ExportType.CSV:
        check_csv_export_rights_on_perimeters(rights=rights, is_nomi=is_nomi)
    else:
        check_jupyter_export_rights_on_perimeters(rights=rights, is_nomi=is_nomi)


class ReviewFilteredPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        q = super(ReviewFilteredPrimaryKeyRelatedField, self).get_queryset()
        creator = self.context.get('request').user
        if can_review_export(creator):
            return q
        else:
            return q.filter(owner=creator)


class ExportRequestListSerializer(serializers.ModelSerializer):
    owner = serializers.SlugRelatedField(read_only=True, slug_field="displayed_name")
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
    cohort = ReviewFilteredPrimaryKeyRelatedField(queryset=CohortResult.objects.all(), source='cohort_fk')
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

    def validate_owner_rights(self, validated_data):
        owner: User = validated_data.get('owner')
        cohort: CohortResult = validated_data.get('cohort_fk')
        perimeters_cohort_ids = cohort.request_query_snapshot.perimeters_ids
        perimeters = Perimeter.objects.filter(cohort_id__in=perimeters_cohort_ids)
        rights = build_data_rights(owner, perimeters)
        check_rights_on_perimeters_for_exports(rights, validated_data.get('output_format'), validated_data.get('nominative'))

    def create(self, validated_data):
        owner: User = validated_data.get('owner')
        check_email_address(owner.email)
        cohort: CohortResult = validated_data.get('cohort_fk')
        creator_is_reviewer = can_review_transfer_jupyter(self.context.get('request').user)

        if not creator_is_reviewer and cohort.owner.pk != owner.pk:
            raise ValidationError("The cohort does not belong to the request owner!")

        if cohort.request_job_status != JobStatus.finished:
            raise ValidationError('The requested cohort has not finished successfully.')

        validated_data['cohort_id'] = validated_data.get('cohort_fk').fhir_group_id

        output_format = validated_data.get('output_format')
        validated_data['motivation'] = validated_data.get('motivation', "").replace("\n", " -- ")

        if output_format == ExportType.HIVE:
            self.validate_hive_export(validated_data, creator_is_reviewer)
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

    def validate_hive_export(self, validated_data: dict, creator_is_reviewer: bool):
        target_unix_account = validated_data.get('target_unix_account')
        if not target_unix_account:
            raise ValidationError("Pour une demande d'export HIVE, il faut fournir target_unix_account")

        owner = validated_data.get('owner')
        if creator_is_reviewer:
            validated_data['request_job_status'] = JobStatus.validated
            validated_data['reviewer_fk'] = self.context.get('request').user
        else:
            if not conf_workspaces.is_user_bound_to_unix_account(owner, target_unix_account.aphp_ldap_group_dn):
                raise ValidationError(f"Le compte Unix destinataire ({target_unix_account.pk}) "
                                      f"n'est pas lié à l'utilisateur voulu ({owner.pk})")
            self.validate_owner_rights(validated_data)

    def validate_csv_export(self, validated_data: dict):
        validated_data['request_job_status'] = JobStatus.validated
        creator: User = self.context.get('request').user

        if validated_data.get('owner').pk != creator.pk:
            raise ValidationError(f"Dans le cas d'une demande d'export CSV, vous ne pouvez pas "
                                  f"générer de demande d'export pour un autre provider_id que le vôtre."
                                  f"Vous êtes connectés en tant que {creator.displayed_name}")
        if not validated_data.get('nominative'):
            raise ValidationError("Actuellement, la demande d'export CSV en pseudo-anonymisée n'est pas possible.")
        self.validate_owner_rights(validated_data)


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
        fields = "__all__"
        read_only_fields = ["uuid",
                            "export",
                            "cohort_result_subset",
                            "respect_table_relationships"]


class ExportSerializer(serializers.ModelSerializer):
    export_tables = ExportTableSerializer(many=True)

    class Meta:
        model = Export
        fields = "__all__"

    def create(self, validated_data):
        export_tables = validated_data.pop("export_tables", [])
        export = super(ExportSerializer, self).create(validated_data)
        export_service.create_tables(http_request=self.context.get("request"),
                                     tables_data=export_tables,
                                     export=export)
        return export


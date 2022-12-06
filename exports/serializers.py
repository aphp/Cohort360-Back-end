from typing import List

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

import workspaces.conf_workspaces as conf_workspaces
from accesses.models import DataRight, build_data_rights
from admin_cohort.models import User, JobStatus
from cohort.models import CohortResult
from exports import conf_exports
from exports.emails import check_email_address
from exports.models import ExportRequest, ExportRequestTable, ExportType
from exports.permissions import can_review_transfer_jupyter, can_review_export
from workspaces.models import Account


class ExportRequestTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportRequestTable
        fields = "__all__"
        read_only_fields = ["export_request_table_id",
                            "target_table_name",
                            "source_table_name",
                            "export_request",
                            "deleted_at"]


def check_rights_on_perimeters_for_exports(rights: List[DataRight], export_type: str, is_nomi: bool):
    if is_nomi:
        wrong_perims = [r.care_site_id for r in rights if not r.right_read_patient_nominative]
        if wrong_perims or not rights:
            raise ValidationError(f"L'utilisateur n'a pas le droit de lecture nominative "
                                  f"actuellement sur les périmètres {wrong_perims}.")
    else:
        wrong_perims = [r.care_site_id for r in rights if not r.right_read_patient_pseudo_anonymised]
        if wrong_perims or not rights:
            raise ValidationError(f"L'utilisateur n'a pas le droit de lecture pseudonymisée "
                                  f"actuellement sur les périmètres {wrong_perims}.")

    if export_type == ExportType.CSV.value:
        if is_nomi:
            wrong_perims = [r.care_site_id for r in rights if not r.right_export_csv_nominative]
        else:
            wrong_perims = [r.care_site_id for r in rights if not r.right_export_csv_pseudo_anonymised]

        if wrong_perims or not rights:
            raise ValidationError(f"Le provider n'a pas le droit d'export {is_nomi and 'nominatif' or 'pseudonymisé'} "
                                  f"actuellement sur les périmètres {wrong_perims}.")

    if export_type in [ExportType.PSQL.value, ExportType.HIVE.value]:
        if is_nomi:
            wrong_perims = [r.care_site_id for r in rights if not r.right_transfer_jupyter_nominative]
        else:
            wrong_perims = [r.care_site_id for r in rights if not r.right_transfer_jupyter_pseudo_anonymised]

        if wrong_perims or not rights:
            raise ValidationError(f"Le provider n'a pas le droit d'export jupyter "
                                  f"{is_nomi and 'nominatif' or 'pseudonymisé'} "
                                  f"actuellement sur les périmètres {wrong_perims}.")


class ReviewFilteredPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        q = super(ReviewFilteredPrimaryKeyRelatedField, self).get_queryset()
        creator = self.context.get('request', None).user
        if can_review_export(creator):
            return q
        else:
            return q.filter(owner=creator)


class ExportRequestSerializer(serializers.ModelSerializer):
    tables = ExportRequestTableSerializer(many=True)
    cohort = ReviewFilteredPrimaryKeyRelatedField(queryset=CohortResult.objects.all(), source='cohort_fk')
    reviewer_fk = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, allow_empty=True,
                                                     required=False)
    cohort_id = serializers.IntegerField(required=False)
    # after database fusion
    # creator = ReducedUserSerializer(allow_null=True, read_only=True)
    # reviewer = ReducedUserSerializer(allow_null=True, read_only=True)

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

    def create_tables(self, tables, req):
        for table in tables:
            # table["export_request"] = req #.id
            ExportRequestTable.objects.create(export_request=req, **table)

    def validate_owner_rights(self, validated_data):
        cont_req: Request = self.context.get('request')
        owner: User = validated_data.get('owner')
        perim_ids = list(map(int, conf_exports.get_cohort_perimeters(validated_data.get('cohort_fk').fhir_group_id,
                                                                     getattr(cont_req, 'jwt_session_key', None))))
        rights = build_data_rights(owner, perim_ids)
        check_rights_on_perimeters_for_exports(rights, validated_data.get('output_format'),
                                               validated_data.get('nominative'))

    def create(self, validated_data):
        owner: User = validated_data.get('owner')
        check_email_address(owner)
        cohort: CohortResult = validated_data.get('cohort_fk')

        creator_is_reviewer = can_review_transfer_jupyter(self.context.get('request').user)

        if not creator_is_reviewer and cohort.owner.pk != owner.pk:
            raise ValidationError("The owner of the request does not own the Cohort requested")

        if cohort.request_job_status != JobStatus.finished and cohort.request_job_status != JobStatus.finished:
            raise ValidationError('The requested cohort has not successfully finished.')

        validated_data['cohort_id'] = validated_data.get('cohort_fk').fhir_group_id

        output_format = validated_data.get('output_format')
        validated_data['motivation'] = validated_data.get('motivation', "").replace("\n", " -- ")

        if output_format in [ExportType.HIVE, ExportType.PSQL]:
            self.validate_sql_hive(validated_data, creator_is_reviewer)
        else:
            self.validate_csv(validated_data)

        tables = validated_data.pop("tables", [])
        req = super(ExportRequestSerializer, self).create(validated_data)

        self.create_tables(tables, req)
        try:
            from exports.tasks import launch_request
            launch_request.delay(req.id)
        except Exception as e:
            req.request_job_status = JobStatus.failed
            req.request_job_fail_msg = f"INTERNAL ERROR: Could not launch celery task: {e}"
        return req

    def validate_sql_hive(self, validated_data, creator_is_reviewer: bool):
        target_unix_account: Account = validated_data.get('target_unix_account', None)
        if target_unix_account is None:
            raise ValidationError("Pour une demande d'export hive, il faut fournir target_unix_account")

        owner = validated_data.get('owner')
        if creator_is_reviewer:
            validated_data['request_job_status'] = JobStatus.validated
            validated_data['reviewer_fk'] = self.context.get('request').user
        else:
            if not conf_workspaces.is_user_bound_to_unix_account(owner, target_unix_account.aphp_ldap_group_dn):
                raise ValidationError(f"Le compte Unix destinataire ({target_unix_account.pk}) "
                                      f"n'est pas lié à l'utilisateur voulu ({owner.pk})")
            self.validate_owner_rights(validated_data)

    def validate_csv(self, validated_data):
        validated_data['request_job_status'] = JobStatus.validated
        creator: User = self.context.get('request').user

        if validated_data.get('owner').pk != creator.pk:
            raise ValidationError(f"Dans le cas d'une demande d'export CSV, vous ne pouvez pas "
                                  f"générer de demande d'export pour un autre provider_id que le vôtre."
                                  f"vous êtes connecté.e en tant que {creator.displayed_name}")
        if not validated_data.get('nominative'):
            raise ValidationError("Actuellement, la demande d'export CSV en pseudo-anonymisée n'est pas possible.")

        self.validate_owner_rights(validated_data)

    def update(self, instance, validated_data):
        raise ValidationError("Update is not authorized. Please use urls /deny or /validate")


class OwnedCohortPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get('request', None)
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

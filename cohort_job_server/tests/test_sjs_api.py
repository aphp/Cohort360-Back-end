import json
from pathlib import Path
from unittest import mock

from django.test import TestCase

from admin_cohort.models import User
from cohort_job_server.apps import CohortJobServerConfig
from cohort_job_server.sjs_api import QueryFormatter, BaseCohortRequest
from cohort_job_server.sjs_api.enums import ResourceType
from cohort_job_server.sjs_api.exceptions import FhirException
from cohort_job_server.sjs_api.schemas import FhirParameters, FhirParameter, CohortQuery


class FhirResponseMapperTest(TestCase):
    def test_map_parameters_to_string_fq_valid(self):
        parameters = FhirParameters(
            resourceType=ResourceType.PROCEDURE,
            parameter=[
                FhirParameter(name="fq", valueString="fq=active:true&fq=active:suppr&fq=gender:male"),
                FhirParameter(name="collection", valueString=ResourceType.PROCEDURE),
            ]
        )
        response = parameters.to_dict()
        self.assertEqual(2, len(response))
        self.assertEqual(ResourceType.PROCEDURE, response["collection"])
        self.assertEqual("fq=active:true&fq=active:suppr&fq=gender:male", response["fq"])

    def test_map_parameters_to_string_fhir_response_empty_list_exception(self):
        parameters = FhirParameters(resourceType=ResourceType.PATIENT, parameter=[])
        with self.assertRaises(FhirException):
            parameters.to_dict()


class CohortQueryTest(TestCase):

    def test_transform_json_to_cohort_query(self):
        with open(Path(__file__).resolve().parent.joinpath("resources/complex_request.json"), "r") as f:
            json_data = json.load(f)
        cohort_query = CohortQuery(**json_data)
        self.assertEqual(len(json_data["request"]["criteria"]), len(cohort_query.criteria.criteria))


class TestQueryFormatter(TestCase):
    def setUp(self):
        def load_query(filename: str) -> CohortQuery:
            with open(Path(__file__).resolve().parent.joinpath(f"resources/{filename}"), "r") as f:
                return CohortQuery(**json.load(f))

        self.auth_headers = {'Authorization': 'Bearer xxx.token.xxx', 'authorizationMethod': 'JWT', 'X-Trace-Id': '12a'}
        self.query_formatter = QueryFormatter(self.auth_headers)
        self.cohort_query_complex = load_query("complex_request.json")
        self.cohort_query_simple = load_query("simple_request.json")
        self.fq_value_string = 'fq=active:true&fq=gender:male'
        self.mocked_query_fhir_result = FhirParameters(
            resourceType=ResourceType.PATIENT,
            parameter=
            [
                FhirParameter(name="fq", valueString=self.fq_value_string),
                FhirParameter(name="collection", valueString=ResourceType.PATIENT),
            ]
        )
        CohortJobServerConfig.USE_SOLR = True

    @mock.patch("cohort_job_server.sjs_api.query_formatter.query_fhir")
    def test_format_to_fhir_simple_query(self, query_fhir):
        query_fhir.return_value = self.mocked_query_fhir_result
        res = self.query_formatter.format_to_fhir(self.cohort_query_simple, False)
        self.assertEqual(1, len(res.criteria))
        res_criteria = res.criteria[0]
        self.assertEqual(ResourceType.DOCUMENT_REFERENCE, res_criteria.resource_type)
        self.assertEqual(self.fq_value_string, res_criteria.filter_solr, )
        self.assertEqual("docstatus=final&type:not=doc-impor&empty=false&patient-active=true&_text=ok",
                          res_criteria.filter_fhir)

    @mock.patch("cohort_job_server.sjs_api.query_formatter.query_fhir")
    def test_format_to_fhir_simple_query_pseudo(self, query_fhir):
        query_fhir.return_value = self.mocked_query_fhir_result
        res = self.query_formatter.format_to_fhir(self.cohort_query_simple, True)
        self.assertEqual(1, len(res.criteria))
        res_criteria = res.criteria[0]
        self.assertEqual(ResourceType.DOCUMENT_REFERENCE, res_criteria.resource_type)
        self.assertEqual(self.fq_value_string, res_criteria.filter_solr, )
        self.assertEqual("docstatus=final&type:not=doc-impor&empty=false&patient-active=true&_text=ok",
                          res_criteria.filter_fhir)

    @mock.patch("cohort_job_server.sjs_api.query_formatter.query_fhir")
    def test_format_to_fhir_complex_query(self, query_fhir):
        query_fhir.return_value = self.mocked_query_fhir_result
        res = self.query_formatter.format_to_fhir(self.cohort_query_complex, False)
        self.assertEqual(6, len(res.criteria))
        res_criteria = res.criteria[1]
        self.assertEqual(ResourceType.CONDITION, res_criteria.resource_type)
        self.assertEqual(self.fq_value_string, res_criteria.filter_solr, )
        self.assertEqual("patient-active=true&codeList=A00-B99", res_criteria.filter_fhir)

    def test_cohort_request_pseudo_read(self):
        user1 = User.objects.create(firstname='Test',
                                    lastname='USER',
                                    email='test.user@aphp.fr',
                                    username='1111111')
        read_in_pseudo = BaseCohortRequest.is_cohort_request_pseudo_read(username=user1.username, source_population=[])
        self.assertTrue(read_in_pseudo)

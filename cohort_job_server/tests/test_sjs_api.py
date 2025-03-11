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


class TestBaseCohortRequest(TestCase):
    def setUp(self):
        self.auth_headers = {'Authorization': 'Bearer xxx.token.xxx', 'authorizationMethod': 'JWT', 'X-Trace-Id': '12a'}
        self.instance_id = "test-instance-id"
        self.json_query = '{"sourcePopulation": {"caresiteCohortList": []}}'
        
    @mock.patch('cohort_job_server.sjs_api.cohort_requests.base_cohort_request.QueryFormatter')
    @mock.patch('cohort_job_server.sjs_api.cohort_requests.base_cohort_request.format_spark_job_request_for_sjs')
    def test_create_sjs_request_with_stage_details(self, mock_format_request, mock_query_formatter):
        # Mock the format_to_fhir method to return a criteria object
        mock_formatter_instance = mock.MagicMock()
        mock_query_formatter.return_value = mock_formatter_instance
        mock_formatter_instance.format_to_fhir.return_value = mock.MagicMock()
        
        # Mock the format_spark_job_request_for_sjs function to return a string
        expected_result = '{"modeOptions": {"sampling": 0.5, "details": "detailed"}}'
        mock_format_request.return_value = expected_result
        
        # Create a BaseCohortRequest with stage_details and sampling
        from cohort_job_server.sjs_api.enums import Mode
        stage_details = "detailed"
        sampling_ratio = 0.5
        request = BaseCohortRequest(
            mode=Mode.COUNT,
            instance_id=self.instance_id,
            json_query=self.json_query,
            auth_headers=self.auth_headers,
            stage_details=stage_details,
            sampling_ratio=sampling_ratio
        )
        
        # Create a mock CohortQuery
        cohort_query = mock.MagicMock()
        
        # Call create_sjs_request
        result = request.create_sjs_request(cohort_query)
        
        # Verify that the result is correct
        self.assertEqual(result, expected_result)
        
        # Verify that format_spark_job_request_for_sjs was called
        mock_format_request.assert_called_once()
        
        # Verify that the SparkJobObject was created with the correct parameters
        spark_job_obj = mock_format_request.call_args[0][0]
        self.assertEqual(spark_job_obj.mode, Mode.COUNT)
        self.assertEqual(spark_job_obj.owner_entity_id, None)  # Not set in our test
        
        # Verify that the result contains the expected values
        self.assertIn('"sampling": 0.5', expected_result)
        self.assertIn('"details": "detailed"', expected_result)


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

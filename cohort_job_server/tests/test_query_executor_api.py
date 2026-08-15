import json
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase

from admin_cohort.models import User
from cohort_job_server.apps import CohortJobServerConfig
from cohort_job_server.query_executor_api import QueryFormatter, BaseCohortRequest
from cohort_job_server.query_executor_api.enums import ResourceType
from cohort_job_server.query_executor_api.exceptions import FhirException
from cohort_job_server.query_executor_api.query_formatter import add_prefix_search_on_ccam_leaves, add_security_params_to_filter_fhir
from cohort_job_server.query_executor_api.schemas import FhirParameters, FhirParameter, CohortQuery, Criteria, SourcePopulation

CCAM = "https://aphp.fr/ig/fhir/core/CodeSystem/CCAMDescriptiveVerAPHP"
ATIH = "https://www.atih.sante.fr/plateformes-de-transmission-et-logiciels/logiciels-espace-de-telechargement/id_lot/3550"
PSEUDED_TOKEN = "http://terminology.hl7.org/CodeSystem/v3-ObservationValue|PSEUDED"


class FhirResponseMapperTest(TestCase):
    def test_map_parameters_to_string_fq_valid(self):
        parameters = FhirParameters(
            resourceType=ResourceType.PROCEDURE,
            parameter=[
                FhirParameter(name="fq", valueString="fq=active:true&fq=active:suppr&fq=gender:male"),
                FhirParameter(name="collection", valueString=ResourceType.PROCEDURE),
            ],
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
        self.auth_headers = {
            "Authorization": "Bearer xxx.token.xxx",
            settings.AUTHORIZATION_METHOD_HEADER: settings.JWT_AUTH_MODE,
            "X-Trace-Id": "12a",
        }
        self.instance_id = "test-instance-id"
        self.json_query = '{"sourcePopulation": {"caresiteCohortList": []}}'

    @mock.patch("cohort_job_server.query_executor_api.cohort_requests.base_cohort_request.QueryFormatter")
    @mock.patch("cohort_job_server.query_executor_api.cohort_requests.base_cohort_request.format_spark_job_request_for_query_executor")
    def test_create_query_executor_request_with_stage_details(self, mock_format_request, mock_query_formatter):
        # Mock the format_to_fhir method to return a criteria object
        mock_formatter_instance = mock.MagicMock()
        mock_query_formatter.return_value = mock_formatter_instance
        mock_formatter_instance.format_to_fhir.return_value = mock.MagicMock()

        # Mock the format_spark_job_request_for_query_executor function to return a string
        expected_result = '{"mode_options": {"sampling": 0.5, "details": "detailed"}}'
        mock_format_request.return_value = expected_result

        # Create a BaseCohortRequest with stage_details and sampling
        from cohort_job_server.query_executor_api.enums import Mode

        stage_details = "detailed"
        sampling_ratio = 0.5
        request = BaseCohortRequest(
            mode=Mode.COUNT,
            instance_id=self.instance_id,
            json_query=self.json_query,
            auth_headers=self.auth_headers,
            stage_details=stage_details,
            sampling_ratio=sampling_ratio,
        )

        # Create a mock CohortQuery
        cohort_query = mock.MagicMock()

        # Call create_query_executor_request
        result = request.create_query_executor_request(cohort_query)

        # Verify that the result is correct
        self.assertEqual(result, expected_result)

        # Verify that format_spark_job_request_for_query_executor was called
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

        self.auth_headers = {
            "Authorization": "Bearer xxx.token.xxx",
            settings.AUTHORIZATION_METHOD_HEADER: settings.JWT_AUTH_MODE,
            "X-Trace-Id": "12a",
        }
        self.query_formatter = QueryFormatter(self.auth_headers)
        self.cohort_query_complex = load_query("complex_request.json")
        self.cohort_query_simple = load_query("simple_request.json")
        self.fq_value_string = "fq=active:true&fq=gender:male"
        self.mocked_query_fhir_result = FhirParameters(
            resourceType=ResourceType.PATIENT,
            parameter=[
                FhirParameter(name="fq", valueString=self.fq_value_string),
                FhirParameter(name="collection", valueString=ResourceType.PATIENT),
            ],
        )
        CohortJobServerConfig.USE_SOLR = True

    @staticmethod
    def sent_fhir_params(query_fhir) -> dict[str, list[str]]:
        """Params actually sent to the FHIR $query operation, asserting on the mocked return is not enough."""
        return query_fhir.call_args[0][1]

    @mock.patch("cohort_job_server.query_executor_api.query_formatter.query_fhir")
    def test_format_to_fhir_simple_query(self, query_fhir):
        query_fhir.return_value = self.mocked_query_fhir_result
        res = self.query_formatter.format_to_fhir(self.cohort_query_simple, False)
        self.assertEqual(1, len(res.criteria))
        res_criteria = res.criteria[0]
        self.assertEqual(ResourceType.DOCUMENT_REFERENCE, res_criteria.resource_type)
        self.assertEqual(
            self.fq_value_string,
            res_criteria.filter_solr,
        )
        self.assertEqual("docstatus=final&type:not=doc-impor&empty=false&patient-active=true&_text=ok", res_criteria.filter_fhir)
        self.assertNotIn("_security", self.sent_fhir_params(query_fhir))
        self.assertEqual(["1234"], self.sent_fhir_params(query_fhir)["_list"])

    @mock.patch("cohort_job_server.query_executor_api.query_formatter.query_fhir")
    def test_format_to_fhir_simple_query_pseudo(self, query_fhir):
        query_fhir.return_value = self.mocked_query_fhir_result
        res = self.query_formatter.format_to_fhir(self.cohort_query_simple, True)
        self.assertEqual(1, len(res.criteria))
        res_criteria = res.criteria[0]
        self.assertEqual(ResourceType.DOCUMENT_REFERENCE, res_criteria.resource_type)
        self.assertEqual(
            self.fq_value_string,
            res_criteria.filter_solr,
        )
        self.assertEqual("docstatus=final&type:not=doc-impor&empty=false&patient-active=true&_text=ok", res_criteria.filter_fhir)
        self.assertEqual([PSEUDED_TOKEN], self.sent_fhir_params(query_fhir)["_security"])
        self.assertEqual(["1234"], self.sent_fhir_params(query_fhir)["_list"])

    @mock.patch("cohort_job_server.query_executor_api.query_formatter.query_fhir")
    def test_format_to_fhir_ipp_list_is_not_pseudonymized(self, query_fhir):
        query_fhir.return_value = self.mocked_query_fhir_result
        query = CohortQuery(
            **{
                "_type": "request",
                "sourcePopulation": {"caresiteCohortList": ["112"]},
                "request": {
                    "_type": "basicResource",
                    "_id": 1,
                    "isInclusive": True,
                    "resourceType": "IPPList",
                    "filterFhir": "identifier.value=8040200003,8000130100",
                },
            }
        )
        res = self.query_formatter.format_to_fhir(query, True)
        self.assertNotIn("_security", self.sent_fhir_params(query_fhir))
        self.assertEqual(["112"], self.sent_fhir_params(query_fhir)["_list"])
        self.assertEqual(f"{self.fq_value_string}&fq=identifier.value:(8040200003 8000130100)", res.filter_solr)

    @mock.patch("cohort_job_server.query_executor_api.query_formatter.query_fhir")
    def test_format_to_fhir_several_care_site_cohorts(self, query_fhir):
        query_fhir.return_value = self.mocked_query_fhir_result
        self.cohort_query_simple.source_population = SourcePopulation(caresiteCohortList=[112, 113])
        self.query_formatter.format_to_fhir(self.cohort_query_simple, False)
        self.assertEqual(["112,113"], self.sent_fhir_params(query_fhir)["_list"])

    @mock.patch("cohort_job_server.query_executor_api.query_formatter.query_fhir")
    def test_format_to_fhir_complex_query(self, query_fhir):
        query_fhir.return_value = self.mocked_query_fhir_result
        res = self.query_formatter.format_to_fhir(self.cohort_query_complex, False)
        self.assertEqual(6, len(res.criteria))
        res_criteria = res.criteria[1]
        self.assertEqual(ResourceType.CONDITION, res_criteria.resource_type)
        self.assertEqual(
            self.fq_value_string,
            res_criteria.filter_solr,
        )
        self.assertEqual("patient-active=true&codeList=A00-B99", res_criteria.filter_fhir)

    def test_cohort_request_pseudo_read(self):
        user1 = User.objects.create(firstname="Test", lastname="USER", email="test.user@aphp.fr", username="1111111")
        read_in_pseudo = BaseCohortRequest.is_cohort_request_pseudo_read(username=user1.username, source_population=[])
        self.assertTrue(read_in_pseudo)

    @mock.patch("cohort_job_server.query_executor_api.query_formatter.query_fhir")
    def test_format_to_fhir_adds_prefix_on_ccam_leaf(self, query_fhir):
        query_fhir.return_value = self.mocked_query_fhir_result
        query = CohortQuery(
            **{
                "_type": "request",
                "sourcePopulation": {"caresiteCohortList": []},
                "request": {
                    "_type": "basicResource",
                    "_id": 1,
                    "isInclusive": True,
                    "resourceType": "Procedure",
                    "filterFhir": f"code={CCAM}|JQGA004",
                },
            }
        )
        res = self.query_formatter.format_to_fhir(query, False)
        self.assertEqual(f"code={CCAM}|JQGA004*", res.filter_fhir)
        self.assertNotIn("_list", self.sent_fhir_params(query_fhir))


class TestCcamLeafStartsWith(TestCase):
    def test_leaf_code_with_system_becomes_prefix(self):
        self.assertEqual(f"code={CCAM}|JQGA004*", add_prefix_search_on_ccam_leaves(f"code={CCAM}|JQGA004", ResourceType.PROCEDURE))

    def test_bare_leaf_code_becomes_prefix(self):
        self.assertEqual("code=JQGA004*", add_prefix_search_on_ccam_leaves("code=JQGA004", ResourceType.PROCEDURE))

    def test_comma_separated_leaves(self):
        self.assertEqual("code=JQGA004*,HGEA002*", add_prefix_search_on_ccam_leaves("code=JQGA004,HGEA002", ResourceType.PROCEDURE))

    def test_numeric_node_becomes_prefix(self):
        # Les noeuds numériques (chapitres/branches) ont aussi été ré-encodés : cherchés en préfixe.
        self.assertEqual("code=000124*", add_prefix_search_on_ccam_leaves("code=000124", ResourceType.PROCEDURE))

    def test_already_wildcarded_is_idempotent(self):
        self.assertEqual("code=JQGA004*", add_prefix_search_on_ccam_leaves("code=JQGA004*", ResourceType.PROCEDURE))

    def test_segmented_activity_code_becomes_prefix(self):
        self.assertEqual("code=JQGA0041201*", add_prefix_search_on_ccam_leaves("code=JQGA0041201", ResourceType.PROCEDURE))

    def test_other_params_untouched(self):
        filter_fhir = f"patient-active=true&code={CCAM}|JQGA004"
        self.assertEqual(f"patient-active=true&code={CCAM}|JQGA004*", add_prefix_search_on_ccam_leaves(filter_fhir, ResourceType.PROCEDURE))

    def test_non_procedure_resource_untouched(self):
        self.assertEqual("code=JQGA004", add_prefix_search_on_ccam_leaves("code=JQGA004", ResourceType.CONDITION))

    def test_empty_filter_untouched(self):
        self.assertEqual("", add_prefix_search_on_ccam_leaves("", ResourceType.PROCEDURE))

    def test_code_modifier_is_expanded(self):
        self.assertEqual("code:not=JQGA004*", add_prefix_search_on_ccam_leaves("code:not=JQGA004", ResourceType.PROCEDURE))

    def test_valueset_modifiers_untouched(self):
        # `code:in` / `code:not-in` portent une URI de ValueSet, jamais wildcardée.
        vs = "https://smt.esante.gouv.fr/terminologie-ccam"
        self.assertEqual(f"code:in={vs}", add_prefix_search_on_ccam_leaves(f"code:in={vs}", ResourceType.PROCEDURE))
        self.assertEqual(f"code:not-in={vs}", add_prefix_search_on_ccam_leaves(f"code:not-in={vs}", ResourceType.PROCEDURE))

    def test_other_code_prefixed_param_untouched(self):
        self.assertEqual("codeList=JQGA004", add_prefix_search_on_ccam_leaves("codeList=JQGA004", ResourceType.PROCEDURE))

    def test_atih_codesystem_becomes_prefix(self):
        self.assertEqual(f"code={ATIH}|JQGA004*", add_prefix_search_on_ccam_leaves(f"code={ATIH}|JQGA004", ResourceType.PROCEDURE))

    def test_non_ccam_codesystem_untouched(self):
        self.assertEqual("code=http://other|JQGA004", add_prefix_search_on_ccam_leaves("code=http://other|JQGA004", ResourceType.PROCEDURE))


class TestAddSecurityParamsToFilterFhir(TestCase):
    @staticmethod
    def criteria(filter_fhir: str | None, resource_type: ResourceType = ResourceType.CONDITION) -> Criteria:
        criteria = Criteria(resourceType=resource_type)
        criteria.filter_fhir = filter_fhir
        return criteria

    def test_pseudo_prepends_security_then_source_population(self):
        enriched = add_security_params_to_filter_fhir(self.criteria("gender=male"), SourcePopulation(caresiteCohortList=[112]), True)
        self.assertEqual(f"_security={PSEUDED_TOKEN}&_list=112&gender=male", enriched)

    def test_nomi_only_prepends_source_population(self):
        enriched = add_security_params_to_filter_fhir(self.criteria("gender=male"), SourcePopulation(caresiteCohortList=[112]), False)
        self.assertEqual("_list=112&gender=male", enriched)

    def test_empty_source_population_adds_no_list(self):
        enriched = add_security_params_to_filter_fhir(self.criteria("gender=male"), SourcePopulation(caresiteCohortList=[]), True)
        self.assertEqual(f"_security={PSEUDED_TOKEN}&gender=male", enriched)

    def test_missing_source_population_adds_no_list(self):
        enriched = add_security_params_to_filter_fhir(self.criteria("gender=male"), None, True)
        self.assertEqual(f"_security={PSEUDED_TOKEN}&gender=male", enriched)

    def test_ipp_list_gets_source_population_but_no_security(self):
        criteria = self.criteria("identifier.value=8040200003", ResourceType.IPP_LIST)
        enriched = add_security_params_to_filter_fhir(criteria, SourcePopulation(caresiteCohortList=[112]), True)
        self.assertEqual("_list=112&identifier.value=8040200003", enriched)

    def test_no_filter_fhir_stays_none(self):
        self.assertIsNone(add_security_params_to_filter_fhir(self.criteria(None), SourcePopulation(caresiteCohortList=[112]), True))

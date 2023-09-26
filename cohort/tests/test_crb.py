# todo: to be refactored to follow the file merging refactoring
# import json
# from pathlib import Path
# from unittest import mock, TestCase
#
# from cohort.crb import Criteria
#
# from cohort.crb import CohortQuery, SourcePopulation
# from cohort.crb.cohort_requests.count import CohortCount
# from cohort.crb.cohort_requests.count_all import CohortCountAll
# from cohort.crb.enums import ResourceType, CriteriaType
# from cohort.crb.exceptions import FhirException
# from cohort.crb.dto import FhirParameters, FhirParameter
# from cohort.crb.format_query import FormatQuery
# from cohort.tests.cohort_app_tests import CohortAppTests
#
#
# class FormatQueryTest(CohortAppTests):
#     @mock.patch("cohort.crb.format_query.query_fhir")
#     def test_format_to_fhir_ipp_list(self, query_fhir):
#         query_fhir.return_value = FhirParameters(
#             ResourceType.PATIENT,
#             [
#                 FhirParameter(name="fq", value="fq=active:true&fq=gender:male"),
#                 FhirParameter(name="collection", value=ResourceType.PATIENT),
#             ]
#         )
#         criteria = Criteria(
#             criteria=[
#                 Criteria(
#                     filter_fhir="identifier.value=123,456,879",
#                     resource_type=ResourceType.IPP_LIST,
#                     criteria_type=CriteriaType.BASIC_RESOURCE
#                 )
#             ]
#         )
#         res = FormatQuery().format_to_fhir(CohortQuery(request=criteria))
#         self.assertEquals(1, len(res.criteria))
#         res_criteria = res.criteria[0]
#         self.assertEquals(ResourceType.IPP_LIST, res_criteria.resource_type)
#         self.assertEquals(
#             "fq=active:true&fq=gender:male&fq=identifier.value:(123 456 879)",
#             res_criteria.filter_solr,
#         )
#         self.assertEquals("identifier.value=123,456,879", res_criteria.filter_fhir)
#
#     @mock.patch("cohort.crb.format_query.query_fhir")
#     def test_format_to_fhir_or_group_sub_criteria(self, query_fhir):
#         query_fhir.return_value = FhirParameters(
#             ResourceType.PROCEDURE,
#             [
#                 FhirParameter(name="fq", value="fq=active:true&fq=active:suppr&fq=gender:male"),
#                 FhirParameter(name="collection", value=ResourceType.PROCEDURE),
#             ]
#         )
#
#         criteria = Criteria(
#             criteria=[
#                 Criteria(
#                     criteria_type=CriteriaType.OR_GROUP,
#                     criteria=[
#                         Criteria(
#                             filter_fhir="active=true&active=suppr&gender=male",
#                             resource_type=ResourceType.PROCEDURE,
#                             criteria_type=CriteriaType.BASIC_RESOURCE
#                         )
#                     ]
#                 )
#             ]
#         )
#         res = FormatQuery().format_to_fhir(CohortQuery(request=criteria))
#         res_criteria = res.criteria[0]
#         sub_res_criteria = res_criteria.criteria[0]
#         self.assertEquals(1, len(res.criteria))
#         self.assertEquals(CriteriaType.OR_GROUP, res_criteria.criteria_type)
#         self.assertEquals("fq=active:true&fq=active:suppr&fq=gender:male", sub_res_criteria.filter_solr)
#         self.assertEquals("active=true&active=suppr&gender=male", sub_res_criteria.filter_fhir)
#         self.assertEquals(ResourceType.PROCEDURE, sub_res_criteria.resource_type)
#
#     def test_load_complex_criteria_json(self):
#         with open(Path(__file__).resolve().parent.joinpath("resources/nested_crb_criteria.json"), "r") as f:
#             json_data = json.load(f)
#
#         for json_criteria in json_data['request']['criteria']:
#             criteria = Criteria(**json_criteria)
#             print(criteria)
#
#     def test_load_cohort_query_from_json(self):
#         with open(Path(__file__).resolve().parent.joinpath("resources/nested_crb_criteria.json"), "r") as f:
#             json_data = json.load(f)
#         cohort_query = CohortQuery(**json_data)
#         self.assertEquals(len(json_data['request']['criteria']), len(cohort_query.request.criteria))
#
#
# class FhirResponseMapperTest(CohortAppTests):
#     def test_map_parameters_to_string_fq_valid(self):
#         parameters = FhirParameters(
#             ResourceType.PROCEDURE,
#             [
#                 FhirParameter(name="fq", value="fq=active:true&fq=active:suppr&fq=gender:male"),
#                 FhirParameter(name="collection", value=ResourceType.PROCEDURE),
#             ]
#         )
#
#         response = parameters.to_dict()
#
#         self.assertEqual(2, len(response))
#         self.assertEqual(ResourceType.PROCEDURE, response["collection"])
#         self.assertEqual("fq=active:true&fq=active:suppr&fq=gender:male", response["fq"])
#
#     def test_map_parameters_to_string_fhir_response_empty_list_exception(self):
#         parameters = FhirParameters(None, [])
#         with self.assertRaises(FhirException):
#             parameters.to_dict()
#
#
# def fetch_aphp_care_site_id_mock():
#     return 123456
#
#
# class CohortCountAllTest(CohortAppTests):
#
#     @mock.patch("cohort.crb.sjs_client.SjsClient")
#     def test_when_count_aphp_with_found_cohort_def_id_then_check_if_source_population_is_updated(
#             self, mock_sjs_client
#     ):
#         mock_sjs_instance = mock_sjs_client.return_value
#         mock_sjs_instance.count.return_value = (mock.Mock(), {"some_key": 123456})
#
#         # Patch the fetch_aphp_care_site_id function with the helper method
#         with mock.patch("cohort.crb.cohort_requests.count_all.fetch_aphp_care_site_id", fetch_aphp_care_site_id_mock):
#             cohort_query = CohortQuery(source_population=SourcePopulation([]))
#             count_all = CohortCountAll(cohort_query_builder=CohortQueryBuilder(username="user 1"),
#                                        sjs_client=mock_sjs_instance)
#             count_all.action(cohort_query)
#
#             self.assertEqual([123456], cohort_query.source_population.care_site_cohort_list)
#
#     def test_when_count_aphp_not_found_cohort_def_id_then_throw_exception(self):
#         cohort_query = CohortQuery(source_population=SourcePopulation([]))
#
#         with self.assertRaises(FhirException):
#             self.cohort_count_aphp.count(cohort_query)
#
#
# class CohortCountTest(CohortAppTests):
#     @mock.patch("cohort.crb.format_query.query_fhir")
#     @mock.patch("cohort.crb.sjs_client.SjsClient")
#     def test_count_valid_request(self, query_fhir, mock_sjs_client):
#         query_fhir.return_value = FhirParameters(
#             ResourceType.PATIENT,
#             [
#                 FhirParameter(name="fq", value="active=true&gender=male"),
#                 FhirParameter(name="collection", value=ResourceType.PATIENT),
#             ]
#         )
#         mock_sjs_instance = mock_sjs_client.return_value
#         mock_sjs_instance.count.return_value = (200, {"some_key": 123456})
#         criteria = Criteria(
#             criteria=[
#                 Criteria(
#                     filter_fhir="active=true&gender=male",
#                     resource_type=ResourceType.PATIENT,
#                     criteria_type=CriteriaType.BASIC_RESOURCE
#                 )
#             ]
#         )
#         cohort_query = CohortQuery(source_population=SourcePopulation([]), request=criteria)
#         count = CohortCount(
#             cohort_query_builder=CohortQueryBuilder(username="user 1"),
#             sjs_client=mock_sjs_instance
#         ).action(cohort_query)
#         self.assertEquals("200", count)
#
#
# class CreateTest(TestCase):
#
#     def test_load_json_and_send_to_sjs(self):
#         with open(Path(__file__).resolve().parent.joinpath("resources/nested_crb_criteria.json"), "r") as f:
#             json_data = json.load(f)
#         cohort_query = CohortQuery(**json_data)

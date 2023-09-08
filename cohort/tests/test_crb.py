from unittest import mock

from cohort.crb import CohortQueryBuilder, FhirRequest, SourcePopulation
from cohort.crb.cohort_requests.count import CohortCount
from cohort.crb.cohort_requests.count_all import CohortCountAll, fetch_aphp_care_site_id
from cohort.crb.enums import ResourceType, CriteriaType
from cohort.crb.exceptions import FhirException
from cohort.crb.fhir_params import FhirParameters, FhirParameter
from cohort.crb.format_query import FormatQuery
from cohort.crb.ranges import Criteria
from cohort.tests.cohort_app_tests import CohortAppTests


class FormatQueryTest(CohortAppTests):
    @mock.patch("cohort.crb.format_query.query_fhir")
    def test_format_to_fhir_ipp_list(self, query_fhir):
        query_fhir.return_value = FhirParameters(
            ResourceType.PATIENT,
            [
                FhirParameter(name="fq", value="fq=active:true&fq=gender:male"),
                FhirParameter(name="collection", value=ResourceType.PATIENT),
            ]
        )
        criteria = Criteria(
            criteria=[
                Criteria(
                    filter_fhir="identifier.value=123,456,879",
                    resource_type=ResourceType.IPP_LIST,
                    criteria_type=CriteriaType.BASIC_RESOURCE
                )
            ]
        )
        res = FormatQuery().format_to_fhir(FhirRequest(request=criteria))
        self.assertEquals(1, len(res.criteria))
        res_criteria = res.criteria[0]
        self.assertEquals(ResourceType.IPP_LIST, res_criteria.resource_type)
        self.assertEquals(
            "fq=active:true&fq=gender:male&fq=identifier.value:(123 456 879)",
            res_criteria.filter_solr,
        )
        self.assertEquals("identifier.value=123,456,879", res_criteria.filter_fhir)

    @mock.patch("cohort.crb.format_query.query_fhir")
    def test_format_to_fhir_or_group_sub_criteria(self, query_fhir):
        query_fhir.return_value = FhirParameters(
            ResourceType.PROCEDURE,
            [
                FhirParameter(name="fq", value="fq=active:true&fq=active:suppr&fq=gender:male"),
                FhirParameter(name="collection", value=ResourceType.PROCEDURE),
            ]
        )

        criteria = Criteria(
            criteria=[
                Criteria(
                    criteria_type=CriteriaType.OR_GROUP,
                    criteria=[
                        Criteria(
                            filter_fhir="active=true&active=suppr&gender=male",
                            resource_type=ResourceType.PROCEDURE,
                            criteria_type=CriteriaType.BASIC_RESOURCE
                        )
                    ]
                )
            ]
        )
        res = FormatQuery().format_to_fhir(FhirRequest(request=criteria))
        res_criteria = res.criteria[0]
        sub_res_criteria = res_criteria.criteria[0]
        self.assertEquals(1, len(res.criteria))
        self.assertEquals(CriteriaType.OR_GROUP, res_criteria.criteria_type)
        self.assertEquals("fq=active:true&fq=active:suppr&fq=gender:male", sub_res_criteria.filter_solr, )
        self.assertEquals("active=true&active=suppr&gender=male", sub_res_criteria.filter_fhir)
        self.assertEquals(ResourceType.PROCEDURE, sub_res_criteria.resource_type)


class FhirResponseMapperTest(CohortAppTests):
    def test_map_parameters_to_string_fq_valid(self):
        parameters = FhirParameters(
            ResourceType.PROCEDURE,
            [
                FhirParameter(name="fq", value="fq=active:true&fq=active:suppr&fq=gender:male"),
                FhirParameter(name="collection", value=ResourceType.PROCEDURE),
            ]
        )

        response = parameters.to_dict()

        self.assertEqual(2, len(response))
        self.assertEqual(ResourceType.PROCEDURE, response["collection"])
        self.assertEqual("fq=active:true&fq=active:suppr&fq=gender:male", response["fq"])

    def test_map_parameters_to_string_fhir_response_empty_list_exception(self):
        parameters = FhirParameters(None, [])
        with self.assertRaises(FhirException):
            parameters.to_dict()


def fetch_aphp_care_site_id_mock():
    return 123456

class CohortCountAllTest(CohortAppTests):

    @mock.patch("cohort.crb.sjs_client.SjsClient")
    def test_when_count_aphp_with_found_cohort_def_id_then_check_if_source_population_is_updated(
        self, mock_sjs_client
    ):
        mock_sjs_instance = mock_sjs_client.return_value
        mock_sjs_instance.count.return_value = (mock.Mock(), {"some_key": 123456})

        # Patch the fetch_aphp_care_site_id function with the helper method
        with mock.patch("cohort.crb.cohort_requests.count_all.fetch_aphp_care_site_id", fetch_aphp_care_site_id_mock):
            fhir_request = FhirRequest(source_population=SourcePopulation([]))
            count_all = CohortCountAll(cohort_query_builder=CohortQueryBuilder(username="user 1"),
                                       sjs_client=mock_sjs_instance)
            count_all.action(fhir_request)

            self.assertEqual([123456], fhir_request.source_population.care_site_cohort_list)
    def test_when_count_aphp_not_found_cohort_def_id_then_throw_exception(self):
        fhir_request = FhirRequest(source_population=SourcePopulation([]))

        with self.assertRaises(FhirException):
            self.cohort_count_aphp.count(fhir_request)


class CohortCountTest(CohortAppTests):
    @mock.patch("cohort.crb.format_query.query_fhir")
    @mock.patch("cohort.crb.sjs_client.SjsClient")
    def test_count_valid_request(self, query_fhir, mock_sjs_client):
        query_fhir.return_value = FhirParameters(
            ResourceType.PATIENT,
            [
                FhirParameter(name="fq", value="active=true&gender=male"),
                FhirParameter(name="collection", value=ResourceType.PATIENT),
            ]
        )
        mock_sjs_instance = mock_sjs_client.return_value
        mock_sjs_instance.count.return_value = (200, {"some_key": 123456})
        criteria = Criteria(
            criteria=[
                Criteria(
                    filter_fhir="active=true&gender=male",
                    resource_type=ResourceType.PATIENT,
                    criteria_type=CriteriaType.BASIC_RESOURCE
                )
            ]
        )
        fhir_request = FhirRequest(source_population=SourcePopulation([]), request=criteria)
        count = CohortCount(
            cohort_query_builder=CohortQueryBuilder(username="user 1"),
            sjs_client=mock_sjs_instance
        ).action(fhir_request)
        self.assertEquals("200", count)

from django.test import TestCase

from cohort.scripts.patch_requests_v150 import replace_date_options_with_filter


class TestPatchRequestsV150(TestCase):
    def test_replace_date_options_with_empty_filter(self):
        query = {
            "resourceType": "Condition",
            "dateRangeList": {
                "dateIsNotNull": True,
                "minDate": "2020-01-01",
                "maxDate": "2020-01-02",
            }
        }
        replace_date_options_with_filter(query)
        self.assertEqual(query["filterFhir"],
                         "_filter=%28recorded-date%20gt%202020-01-01%20and%20recorded-date%20lt%202020-01-02%29%20or%20not%20%28date%20eq%20%22%2A%22%29")

    def test_replace_date_options_with_implicit_date_null(self):
        query = {
            "resourceType": "Condition",
            "dateRangeList": {
                "minDate": "2020-01-01",
                "maxDate": "2020-01-02",
            },
            "filterFhir": "SomeFilterA=ddfdsf"
        }
        replace_date_options_with_filter(query)
        self.assertEqual(query["filterFhir"],
                         "SomeFilterA=ddfdsf&_filter=%28recorded-date%20gt%202020-01-01%20and%20recorded-date%20lt%202020-01-02%29%20or%20not%20%28date%20eq%20%22%2A%22%29")

    def test_replace_date_options_with_no_daterange(self):
        query = {
            "resourceType": "Condition",
            "filterFhir": "SomeFilterA=ddfdsf"
        }
        replace_date_options_with_filter(query)
        assert query["filterFhir"] == "SomeFilterA=ddfdsf"

    def test_replace_date_options_with_single_date(self):
        query = {
            "resourceType": "Condition",
            "dateRangeList": {
                "dateIsNotNull": True,
                "minDate": "2020-01-01"
            },
            "filterFhir": "SomeFilterA=ddfdsf"
        }
        replace_date_options_with_filter(query)
        self.assertEqual(query["filterFhir"],
                         "SomeFilterA=ddfdsf&_filter=%28recorded-date%20gt%202020-01-01%29%20or%20not%20%28date%20eq%20%22%2A%22%29")

    def test_replace_date_options_with_full(self):
        query = {
            "resourceType": "Condition",
            "dateRangeList": {
                "dateIsNotNull": False,
                "minDate": "2020-01-01",
                "maxDate": "2020-01-02",
            },
            "filterFhir": "SomeFilterA=ddfdsf"
        }
        replace_date_options_with_filter(query)
        self.assertEqual(query["filterFhir"],
                         "SomeFilterA=ddfdsf&recorded-date=gt2020-01-01&recorded-date=lt2020-01-02")

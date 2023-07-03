import dataclasses
import json

from admin_cohort.tools.tests_tools import BaseTests
from cohort.patches.query_request_updater import QueryRequestUpdater


class TestQueryRequestUpdater(BaseTests):

    def test_update_old_query_snapshots(self):
        new_version = "turbo2000"
        filter_mapping = {
            "SomeResourceA": {
                "SomeFilterA": "SomeFilterB"
            }
        }
        filter_names_to_skip = {
            "SomeResourceB": ["SomeFilterA"]
        }
        filter_values_mapping = {
            "SomeResourceC": {
                "SomeFilterA": {
                    "SomeValueA": "SomeValueB"
                }
            }
        }
        static_required_filters = {
            "SomeResourceB": ["SomeRequiredFilter=SomeValue"]
        }
        resource_name_mapping = {
            "SomeResourceB": "SomeResourceC"
        }

        queries = [
            Request(json.dumps(
                {"version": "1", "_type": "request", "request": {"criteria": [
                    {"filterFhir": "SomeFilterA=some query && true&SomeFilterC=SomeValueC",
                     "resourceType": "SomeResourceA"}]}}
            )),
            Request(json.dumps(
                {"version": "1", "_type": "InnerJoin",
                 "child": [{"fhirFilter": "SomeFilterA=SomeValueA", "resourceType": "SomeResourceB"}]}
            )),
            Request(json.dumps(
                {"version": new_version}
            )),
            Request(json.dumps(
                {"version": "1", "_type": "resource", "fhirFilter": "SomeFilterA=SomeValueA",
                 "resourceType": "SomeResourceC"}
            )),
        ]

        updater = QueryRequestUpdater(
            version_name=new_version,
            filter_mapping=filter_mapping,
            filter_names_to_skip=filter_names_to_skip,
            filter_values_mapping=filter_values_mapping,
            static_required_filters=static_required_filters,
            resource_name_mapping=resource_name_mapping
        )

        saved = []
        updater.do_update_old_query_snapshots(queries, lambda r: saved.append(r.serialized_query), dry_run=False,
                                              debug=False)
        self.assertEquals(len(saved), 3)

        expected = [
            json.dumps({"version": "turbo2000", "_type": "request", "request": {"criteria": [
                {"filterFhir": "SomeFilterB=some query && true&SomeFilterC=SomeValueC",
                 "resourceType": "SomeResourceA"}]}}),
            json.dumps({"version": "turbo2000", "_type": "InnerJoin",
                        "child": [{"fhirFilter": "SomeRequiredFilter=SomeValue", "resourceType": "SomeResourceC"}]}),
            json.dumps({"version": "turbo2000", "_type": "resource", "fhirFilter": "SomeFilterA=SomeValueB",
                        "resourceType": "SomeResourceC"})
        ]
        self.assertEquals(expected[0], saved[0])
        self.assertEquals(expected[1], saved[1])
        self.assertEquals(expected[2], saved[2])


@dataclasses.dataclass
class Request:
    serialized_query: str

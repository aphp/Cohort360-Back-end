import dataclasses
import json

from admin_cohort.tests.tests_tools import BaseTests
from cohort.scripts.patch_requests_v145 import return_filter_if_not_exist
from cohort.scripts.patch_requests_v163 import replace_ccam_root_with_match_all, updater
from cohort.scripts.query_request_updater import QueryRequestUpdater

CCAM = "https://aphp.fr/ig/fhir/core/CodeSystem/CCAMDescriptiveVerAPHP"


class TestQueryRequestUpdater(BaseTests):
    def test_update_old_query_snapshots(self):
        new_version = "turbo2000"
        previous_version_name = "1"
        filter_mapping = {"SomeResourceA": {"SomeFilterA": "SomeFilterB"}}
        filter_names_to_skip = {"SomeResourceB": ["SomeFilterA"]}
        filter_values_mapping = {"SomeResourceC": {"SomeFilterA": {"SomeValueA": "SomeValueB"}}}
        static_required_filters = {
            "SomeResourceB": ["SomeRequiredFilter=SomeValue"],
            "SomeResourceD": [
                lambda filters: return_filter_if_not_exist(filters, "SomeFilterA", "ge0,le0"),
                lambda filters: return_filter_if_not_exist(filters, "SomeFilterB", "ge0,le0"),
            ],
        }
        resource_name_mapping = {"SomeResourceB": "SomeResourceC"}

        queries = [
            Request(
                json.dumps(
                    {
                        "version": "1",
                        "_type": "request",
                        "request": {
                            "criteria": [{"filterFhir": "SomeFilterA=some query && true&SomeFilterC=SomeValueC", "resourceType": "SomeResourceA"}]
                        },
                    }
                )
            ),
            Request(
                json.dumps(
                    {"version": "1", "_type": "InnerJoin", "child": [{"fhirFilter": "SomeFilterA=SomeValueA", "resourceType": "SomeResourceB"}]}
                )
            ),
            Request(json.dumps({"version": new_version})),
            Request(json.dumps({"version": "1", "_type": "resource", "fhirFilter": "SomeFilterA=SomeValueA", "resourceType": "SomeResourceC"})),
            Request(json.dumps({"version": "1", "_type": "resource", "fhirFilter": "SomeFilterA=ExistingValue", "resourceType": "SomeResourceD"})),
        ]

        updater = QueryRequestUpdater(
            version_name=new_version,
            previous_version_name=previous_version_name,
            filter_mapping=filter_mapping,
            filter_names_to_skip=filter_names_to_skip,
            filter_values_mapping=filter_values_mapping,
            static_required_filters=static_required_filters,
            resource_name_mapping=resource_name_mapping,
        )

        saved = []
        updater.do_update_old_query_snapshots(queries, lambda r: saved.append(r.serialized_query), dry_run=False, debug=False)
        self.assertEqual(len(saved), 4)

        expected = [
            json.dumps(
                {
                    "version": "turbo2000",
                    "_type": "request",
                    "request": {
                        "criteria": [{"filterFhir": "SomeFilterB=some query && true&SomeFilterC=SomeValueC", "resourceType": "SomeResourceA"}]
                    },
                }
            ),
            json.dumps(
                {
                    "version": "turbo2000",
                    "_type": "InnerJoin",
                    "child": [{"fhirFilter": "SomeRequiredFilter=SomeValue", "resourceType": "SomeResourceC"}],
                }
            ),
            json.dumps({"version": "turbo2000", "_type": "resource", "fhirFilter": "SomeFilterA=SomeValueB", "resourceType": "SomeResourceC"}),
            json.dumps(
                {
                    "version": "turbo2000",
                    "_type": "resource",
                    "fhirFilter": "SomeFilterA=ExistingValue&SomeFilterB=ge0,le0",
                    "resourceType": "SomeResourceD",
                }
            ),
        ]
        self.assertEqual(expected[0], saved[0])
        self.assertEqual(expected[1], saved[1])
        self.assertEqual(expected[2], saved[2])
        self.assertEqual(expected[3], saved[3])


@dataclasses.dataclass
class Request:
    serialized_query: str


class TestPatchRequestsV163(BaseTests):
    def test_bare_root_becomes_match_all(self):
        self.assertEqual("*", replace_ccam_root_with_match_all("000001"))

    def test_root_with_system_becomes_match_all(self):
        self.assertEqual("*", replace_ccam_root_with_match_all(f"{CCAM}|000001"))

    def test_leaf_code_left_untouched(self):
        self.assertEqual(f"{CCAM}|JQGA004", replace_ccam_root_with_match_all(f"{CCAM}|JQGA004"))

    def test_numeric_branch_node_left_untouched(self):
        self.assertEqual(f"{CCAM}|000124", replace_ccam_root_with_match_all(f"{CCAM}|000124"))

    def test_only_root_token_replaced_in_list(self):
        self.assertEqual(f"*,{CCAM}|JQGA004", replace_ccam_root_with_match_all(f"{CCAM}|000001,{CCAM}|JQGA004"))

    def test_end_to_end_procedure_criteria(self):
        query = {
            "version": "v1.6.2",
            "_type": "resource",
            "resourceType": "Procedure",
            "fhirFilter": f"code={CCAM}|000001",
        }
        saved = []
        updater.do_update_old_query_snapshots([Request(json.dumps(query))], lambda r: saved.append(r.serialized_query), dry_run=False, debug=False)
        self.assertEqual(1, len(saved))
        result = json.loads(saved[0])
        self.assertEqual("v1.6.3", result["version"])
        self.assertEqual("code=*", result["fhirFilter"])

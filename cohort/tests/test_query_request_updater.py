import dataclasses
import json
from unittest.mock import patch

from admin_cohort.tests.tests_tools import BaseTests
from cohort.scripts import query_request_updater as query_request_updater_module
from cohort.scripts.patch_requests_v145 import return_filter_if_not_exist
from cohort.scripts.patch_requests_v162 import CCAM_OLD_CODESYSTEM, map_ccam_code_token, map_ccam_codes, updater_v162
from cohort.scripts.patch_requests_v163 import replace_ccam_root_with_match_all, updater
from cohort.scripts.patch_requests_v164 import map_ccam_codes as map_ccam_codes_v164, updater_v164
from cohort.scripts.patch_requests_v170 import updater_v170
from cohort.scripts.query_request_updater import QueryRequestUpdater

CCAM = "https://aphp.fr/ig/fhir/core/CodeSystem/CCAMDescriptiveVerAPHP"


class TestQueryRequestUpdater(BaseTests):
    def test_skip_filter_accepts_names_and_predicates(self):
        updater = QueryRequestUpdater(
            version_name="2",
            previous_version_name="1",
            filter_mapping={},
            filter_names_to_skip={"SomeResource": ["SomeFilterA", lambda name, value: value == "SkipMe"]},
            filter_values_mapping={},
            static_required_filters={},
            resource_name_mapping={},
        )

        updated_filter, changed = updater.process_filters(["SomeFilterA=x", "SomeFilterB=SkipMe", "SomeFilterC=Keep"], "SomeResource")

        self.assertEqual("SomeFilterC=Keep", updated_filter)
        self.assertTrue(changed)

    def test_filter_fragment_without_equals_sign_is_preserved(self):
        updater = QueryRequestUpdater(
            version_name="2",
            previous_version_name="1",
            filter_mapping={},
            filter_names_to_skip={},
            filter_values_mapping={},
            static_required_filters={},
            resource_name_mapping={},
        )
        original_filter = "code=https://example.org/CodeSystem/observation|123&urn:oid:1.2.3|456,urn:oid:1.2.4|789"
        resource = {"resourceType": "Observation", "fhirFilter": original_filter}

        changed = updater.process_resource(resource, "fhirFilter")

        self.assertEqual(original_filter, resource["fhirFilter"])
        self.assertFalse(changed)

    def test_filter_value_can_contain_equals_signs(self):
        updater = QueryRequestUpdater(
            version_name="2",
            previous_version_name="1",
            filter_mapping={},
            filter_names_to_skip={},
            filter_values_mapping={},
            static_required_filters={},
            resource_name_mapping={},
        )

        updated_filter, changed = updater.process_filters(["SomeFilter=SomeValue=WithEquals"], "SomeResource")

        self.assertEqual("SomeFilter=SomeValue=WithEquals", updated_filter)
        self.assertFalse(changed)

    def test_update_old_filters_does_not_build_request_query_snapshot(self):
        updater = QueryRequestUpdater(
            version_name="2",
            previous_version_name="1",
            filter_mapping={"SomeResource": {"SomeFilterA": "SomeFilterB"}},
            filter_names_to_skip={},
            filter_values_mapping={},
            static_required_filters={},
            resource_name_mapping={},
        )
        resource_filter = Filter(uuid="filter-uuid", query_version="1", fhir_resource="SomeResource", filter="SomeFilterA=SomeValue")

        with patch.object(query_request_updater_module.FhirFilter.objects, "all", return_value=[resource_filter]):
            updater.update_old_filters(dry_run=False, debug=False)

        self.assertEqual("2", resource_filter.query_version)
        self.assertEqual("SomeFilterB=SomeValue", resource_filter.filter)
        self.assertTrue(resource_filter.saved)

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


@dataclasses.dataclass
class Filter:
    uuid: str
    query_version: str
    fhir_resource: str
    filter: str
    saved: bool = False

    def save(self):
        self.saved = True


class TestPatchRequestsV162(BaseTests):
    def test_old_code_system_is_replaced_without_changing_code(self):
        self.assertEqual(f"{CCAM}|JQGA004", map_ccam_code_token(f"{CCAM_OLD_CODESYSTEM}|JQGA004"))

    def test_bare_code_gets_new_code_system(self):
        self.assertEqual(f"{CCAM}|JQGA004", map_ccam_code_token("JQGA004"))

    def test_new_code_system_is_left_untouched(self):
        self.assertEqual(f"{CCAM}|JQGA004", map_ccam_code_token(f"{CCAM}|JQGA004"))

    def test_other_code_system_is_left_untouched(self):
        other_code = "https://example.org/CodeSystem/other|JQGA004"
        self.assertEqual(other_code, map_ccam_code_token(other_code))

    def test_multiple_codes_are_converted_independently(self):
        other_code = "https://example.org/CodeSystem/other|OTHER"
        codes = f"{CCAM_OLD_CODESYSTEM}|JQGA004,JQGA005,{CCAM}|JQGA006,{other_code}"
        expected = f"{CCAM}|JQGA004,{CCAM}|JQGA005,{CCAM}|JQGA006,{other_code}"
        self.assertEqual(expected, map_ccam_codes(codes))

    def test_end_to_end_procedure_criteria(self):
        query = {
            "version": "v1.6.1",
            "_type": "resource",
            "resourceType": "Procedure",
            "fhirFilter": f"code={CCAM_OLD_CODESYSTEM}|JQGA004",
        }
        saved = []
        updater_v162.do_update_old_query_snapshots(
            [Request(json.dumps(query))], lambda r: saved.append(r.serialized_query), dry_run=False, debug=False
        )
        self.assertEqual(1, len(saved))
        result = json.loads(saved[0])
        self.assertEqual("v1.6.2", result["version"])
        self.assertEqual(f"code={CCAM}|JQGA004", result["fhirFilter"])


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


class TestPatchRequestsV164(BaseTests):
    def test_bare_act_is_replaced_by_root_wildcard(self):
        self.assertEqual(f"{CCAM}|JQGA004*", map_ccam_codes_v164(f"{CCAM}|JQGA004"))

    def test_segmented_act_is_kept_and_completed(self):
        self.assertEqual(f"{CCAM}|JQGA004...01,{CCAM}|JQGA004*", map_ccam_codes_v164(f"{CCAM}|JQGA004...01"))
        self.assertEqual(f"{CCAM}|JQGA004-001,{CCAM}|JQGA004*", map_ccam_codes_v164(f"{CCAM}|JQGA004-001"))

    def test_truncated_selection_keeps_both_codes(self):
        codes = f"{CCAM}|JQGA004...04,{CCAM}|JQGA004...01"
        expected = f"{CCAM}|JQGA004...04,{CCAM}|JQGA004*,{CCAM}|JQGA004...01"
        self.assertEqual(expected, map_ccam_codes_v164(codes))

    def test_distinct_acts_get_their_own_wildcard(self):
        codes = f"{CCAM}|JQGA004...01,{CCAM}|HGEA002-1101"
        expected = f"{CCAM}|JQGA004...01,{CCAM}|JQGA004*,{CCAM}|HGEA002-1101,{CCAM}|HGEA002*"
        self.assertEqual(expected, map_ccam_codes_v164(codes))

    def test_numeric_node_untouched(self):
        self.assertEqual(f"{CCAM}|001472", map_ccam_codes_v164(f"{CCAM}|001472"))

    def test_match_all_untouched(self):
        self.assertEqual("*", map_ccam_codes_v164("*"))

    def test_non_ccam_system_untouched(self):
        other = "https://terminology.hl7.org/CodeSystem/other"
        self.assertEqual(f"{other}|JQGA004", map_ccam_codes_v164(f"{other}|JQGA004"))

    def test_is_idempotent(self):
        once = map_ccam_codes_v164(f"{CCAM}|JQGA004...01")
        self.assertEqual(once, map_ccam_codes_v164(once))

    def test_end_to_end_procedure_criteria(self):
        query = {
            "version": "v1.6.3",
            "_type": "resource",
            "resourceType": "Procedure",
            "fhirFilter": f"subject.active=true&code={CCAM}|JQGA004...04,{CCAM}|JQGA004...01",
        }
        saved = []
        updater_v164.do_update_old_query_snapshots(
            [Request(json.dumps(query))], lambda r: saved.append(r.serialized_query), dry_run=False, debug=False
        )
        self.assertEqual(1, len(saved))
        result = json.loads(saved[0])
        self.assertEqual("v1.6.4", result["version"])
        expected = f"subject.active=true&code={CCAM}|JQGA004...04,{CCAM}|JQGA004*,{CCAM}|JQGA004...01"
        self.assertEqual(expected, result["fhirFilter"])


@dataclasses.dataclass
class Snapshot:
    uuid: str
    request_id: str
    serialized_query: str
    deleted: object = None
    saved: bool = False

    def save(self):
        self.saved = True


class TestPatchRequestsV170(BaseTests):
    @staticmethod
    def request(*criteria, version="v1.6.4"):
        return {"version": version, "_type": "request", "request": {"_type": "andGroup", "criteria": list(criteria)}}

    @staticmethod
    def run_updater(*queries):
        saved = []
        upgraded = updater_v170.do_update_old_query_snapshots(
            [Request(json.dumps(q)) for q in queries], lambda r: saved.append(json.loads(r.serialized_query)), dry_run=False, debug=False
        )
        return saved, upgraded

    def test_removes_encounter_params_on_observation(self):
        criterion = {
            "_type": "basicResource",
            "resourceType": "Observation",
            "filterFhir": "subject.active=true&code=http://loinc|123&encounter.status=finished&encounter.period-start=ge2024-01-01"
            "&encounter.period-end=le2024-12-31&encounter.service-provider=8312002244&encounter.identifier=12345"
            "&value-quantity=ge10&date=ge2024-01-01",
        }
        saved, upgraded = self.run_updater(self.request(criterion))

        self.assertEqual(1, len(upgraded))
        self.assertEqual("v1.7.0", saved[0]["version"])
        self.assertEqual(
            "subject.active=true&code=http://loinc|123&value-quantity=ge10&date=ge2024-01-01",
            saved[0]["request"]["criteria"][0]["filterFhir"],
        )

    def test_removes_url_encoded_encounter_param(self):
        criterion = {"_type": "basicResource", "resourceType": "Observation", "filterFhir": "code=123&encounter%2Estatus=finished"}
        saved, _ = self.run_updater(self.request(criterion))

        self.assertEqual("code=123", saved[0]["request"]["criteria"][0]["filterFhir"])

    def test_removes_encounter_in_null_filter_and_keeps_date_null_filter(self):
        encounter_filter = '_filter=(encounter.period-start ge 2024-01-01T00:00:00Z) or not (encounter.period-start eq "*")'
        date_filter = '_filter=(date ge 2024-01-01T00:00:00Z) or not (date eq "*")'
        criterion = {"_type": "basicResource", "resourceType": "Observation", "filterFhir": f"code=123&{encounter_filter}&{date_filter}"}
        saved, _ = self.run_updater(self.request(criterion))

        self.assertEqual(f"code=123&{date_filter}", saved[0]["request"]["criteria"][0]["filterFhir"])

    def test_removes_patient_age_on_observation(self):
        criterion = {
            "_type": "basicResource",
            "resourceType": "Observation",
            "filterFhir": "code=123",
            "patientAge": {"minAge": "18-0-0", "maxAge": "65-0-0"},
        }
        saved, upgraded = self.run_updater(self.request(criterion))

        self.assertEqual(1, len(upgraded))
        self.assertNotIn("patientAge", saved[0]["request"]["criteria"][0])
        self.assertEqual("code=123", saved[0]["request"]["criteria"][0]["filterFhir"])

    def test_keeps_other_resources(self):
        criteria = [
            {
                "_type": "basicResource",
                "resourceType": resource,
                "filterFhir": "code=123&encounter.status=finished",
                "patientAge": {"minAge": "18-0-0", "maxAge": None},
            }
            for resource in ("Condition", "Procedure", "MedicationRequest", "ImagingStudy")
        ]
        saved, upgraded = self.run_updater(self.request(*criteria))

        self.assertEqual([], upgraded)
        self.assertEqual(criteria, saved[0]["request"]["criteria"])

    def test_observation_without_encounter_is_unchanged(self):
        query = self.request({"_type": "basicResource", "resourceType": "Observation", "filterFhir": "code=123&date=ge2024-01-01"})
        saved, upgraded = self.run_updater(query)

        self.assertEqual([], upgraded)
        self.assertEqual({**query, "version": "v1.7.0"}, saved[0])

    def test_null_patient_age_is_removed_without_upgrade(self):
        criterion = {"_type": "basicResource", "resourceType": "Observation", "filterFhir": "code=123", "patientAge": None}
        saved, upgraded = self.run_updater(self.request(criterion))

        self.assertEqual([], upgraded)
        self.assertNotIn("patientAge", saved[0]["request"]["criteria"][0])

    def test_nested_group(self):
        criterion = {"_type": "basicResource", "resourceType": "Observation", "filterFhir": "code=123&encounter.status=finished"}
        saved, upgraded = self.run_updater(self.request({"_type": "orGroup", "criteria": [criterion]}))

        self.assertEqual(1, len(upgraded))
        self.assertEqual("code=123", saved[0]["request"]["criteria"][0]["criteria"][0]["filterFhir"])

    def test_only_previous_version_is_migrated(self):
        criterion = {"_type": "basicResource", "resourceType": "Observation", "filterFhir": "code=123&encounter.status=finished"}
        saved, upgraded = self.run_updater(self.request(criterion, version="v1.6.3"), self.request(criterion, version="v1.7.0"))

        self.assertEqual([], saved)
        self.assertEqual([], upgraded)

    def test_update_old_filters(self):
        biology_filter = Filter(uuid="bio", query_version="v1.6.4", fhir_resource="Observation", filter="code=123&encounter.status=finished")
        other_filter = Filter(uuid="other", query_version="v1.6.4", fhir_resource="Condition", filter="code=I10&encounter.status=finished")

        with patch.object(query_request_updater_module.FhirFilter.objects, "all", return_value=[biology_filter, other_filter]):
            upgraded = updater_v170.update_old_filters(dry_run=False, debug=False)

        self.assertEqual(["bio"], [f.filter_uuid for f in upgraded])
        self.assertEqual("code=123", biology_filter.filter)
        self.assertEqual("v1.7.0", biology_filter.query_version)
        self.assertEqual("code=I10&encounter.status=finished", other_filter.filter)
        self.assertEqual("v1.7.0", other_filter.query_version)

    def test_dry_run_returns_recap_without_saving(self):
        impacted = self.request({"_type": "basicResource", "resourceType": "Observation", "filterFhir": "code=123&encounter.status=finished"})
        not_impacted = self.request({"_type": "basicResource", "resourceType": "Observation", "filterFhir": "code=123"})
        snapshots = [
            Snapshot(uuid="s1", request_id="r1", serialized_query=json.dumps(impacted)),
            Snapshot(uuid="s2", request_id="r1", serialized_query=json.dumps(impacted)),
            Snapshot(uuid="s3", request_id="r2", serialized_query=json.dumps(impacted), deleted="2026-01-01"),
            Snapshot(uuid="s4", request_id="r3", serialized_query=json.dumps(not_impacted)),
        ]
        bio_filter = Filter(uuid="bio", query_version="v1.6.4", fhir_resource="Observation", filter="encounter.status=finished")

        with (
            patch.object(query_request_updater_module.RequestQuerySnapshot.objects, "all", return_value=snapshots),
            patch.object(query_request_updater_module.FhirFilter.objects, "all", return_value=[bio_filter]),
            patch.object(query_request_updater_module.CohortResult.objects, "filter") as cohorts,
            patch.object(updater_v170, "log_recap_table") as log_recap,
        ):
            cohorts.return_value.count.return_value = 5
            updater_v170.update_old_query_snapshots(dry_run=True, debug=False, with_filters=True)

        log_recap.assert_called_once_with({"snapshots": 3, "active_snapshots": 2, "requests": 1, "cohorts": 5, "filters": 1}, True)
        cohorts.assert_called_once_with(request_query_snapshot_id__in=["s1", "s2"])
        self.assertFalse(any(s.saved for s in snapshots))
        self.assertFalse(bio_filter.saved)

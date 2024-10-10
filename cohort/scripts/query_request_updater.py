import json
import logging
import tempfile
from functools import reduce
from pathlib import Path
from typing import List, Tuple, TypeVar, Callable, Any, Optional, Dict, Union

from django.db.backends.base.base import BaseDatabaseWrapper

from cohort.models import RequestQuerySnapshot, FhirFilter

LOGGER = logging.getLogger("info")

RESOURCE_DEFAULT = "_"
MATCH_ALL_VALUES = "__MATCH_ALL_VALUES__"


def find_mapped_code(code: str, src_system: str, target_system: str, default_value: Callable[[str], str],
                     db: BaseDatabaseWrapper, code_mapping_cache: Dict[str, str]) -> str:
    if code in code_mapping_cache:
        return code_mapping_cache[code]
    LOGGER.info(f"Searching for code {code}")
    cursor = db.cursor()
    q = '''
        WITH src_codes AS (
            SELECT source_concept_id as src_id,source_concept_code as src_code 
            FROM omop.concept_fhir 
            WHERE source_vocabulary_reference = %s AND delete_datetime IS NULL
            ),
            target_codes AS (
            SELECT source_concept_id as target_id,source_concept_code as target_code 
            FROM omop.concept_fhir 
            WHERE source_vocabulary_reference = %s AND delete_datetime IS NULL
            )
        SELECT target_code FROM omop.concept_relationship r
        INNER JOIN src_codes o
        ON o.src_id = r.concept_id_1
        INNER JOIN target_codes a
        ON a.target_id = r.concept_id_2
        WHERE relationship_id = 'Maps to' AND r.delete_datetime IS NULL AND o.src_code = %s;
        '''
    cursor.execute(q, (src_system, target_system, code))
    res = cursor.fetchone()
    if not res:
        LOGGER.info(f"Failed to find related atc code {code}")
        code_mapping_cache[code] = default_value(code)
        return code_mapping_cache[code]
    code_mapping_cache[code] = target_system + "|" + res[0]
    return code_mapping_cache[code]


class QueryRequestUpdater:
    def __init__(self,
                 version_name: str,
                 previous_version_name: Optional[List[str]],
                 filter_mapping: Dict[str, Dict[str, str]],
                 filter_names_to_skip: Dict[str, List[str]],
                 filter_values_mapping: Dict[str, Dict[str, Dict[str, Union[str, Callable[[str], str]]]]],
                 static_required_filters: Dict[str, List[Union[str, Callable[[List[str]], Optional[str]]]]],
                 resource_name_mapping: Dict[str, str],
                 post_process_basic_resource: Optional[Callable[[Any], bool]] = lambda x: False,
                 post_process_group_resource: Optional[Callable[[Any], bool]] = lambda x: False,
                 ):
        self.version_name = version_name
        self.previous_version_name = previous_version_name
        self.filter_mapping = filter_mapping
        self.filter_names_to_skip = filter_names_to_skip
        self.filter_values_mapping = filter_values_mapping
        self.static_required_filters = static_required_filters
        self.resource_name_mapping = resource_name_mapping
        self.post_process_basic_resource = post_process_basic_resource
        self.post_process_group_resource = post_process_group_resource

    def map_resource_name(self, resource_name: str) -> Tuple[str, bool]:
        if resource_name in self.resource_name_mapping:
            return self.resource_name_mapping[resource_name], True
        return resource_name, False

    def map_filter_name(self, filter_name: str, resource: str) -> Tuple[str, bool]:
        if resource in self.filter_mapping and filter_name in self.filter_mapping[resource]:
            new_name = self.filter_mapping[resource][filter_name]
            LOGGER.info(f"Remapping {filter_name} for {resource} into {new_name}")
            return new_name, True
        elif RESOURCE_DEFAULT in self.filter_mapping and filter_name in self.filter_mapping[RESOURCE_DEFAULT]:
            new_name = self.filter_mapping[RESOURCE_DEFAULT][filter_name]
            LOGGER.info(f"Remapping {filter_name} for {resource} into {new_name}")
            return new_name, True
        return filter_name, False

    def map_filter_value(self, filter_name: str, resource: str, filter_value: str) -> Tuple[str, bool]:
        if resource in self.filter_values_mapping and filter_name in self.filter_values_mapping[resource]:
            if filter_value in self.filter_values_mapping[resource][filter_name]:
                return self.filter_values_mapping[resource][filter_name][filter_value], True
            elif MATCH_ALL_VALUES in self.filter_values_mapping[resource][filter_name]:
                new_val = self.filter_values_mapping[resource][filter_name][MATCH_ALL_VALUES](filter_value)
                return new_val, True
        return filter_value, False

    def add_static_required_filters(self, filters: List[str], resource: str) -> bool:
        has_changed = False
        if resource in self.static_required_filters:
            for static_filter in self.static_required_filters[resource]:
                if callable(static_filter):
                    new_filter = static_filter([*filters])
                    if new_filter:
                        has_changed = True
                        filters.append(new_filter)
                elif static_filter not in filters:
                    has_changed = True
                    filters.append(static_filter)
        return has_changed

    def skip_filter(self, filter_name, resource) -> bool:
        return resource in self.filter_names_to_skip and filter_name in self.filter_names_to_skip[resource]

    def process_filters(self, filter_items: List[str], resource: str) -> Tuple[str, bool]:
        updated_filters = []
        changed = False
        for filter_item in filter_items:
            if filter_item.strip():
                filter_name, filter_value = filter_item.split("=")
                if not self.skip_filter(filter_name, resource):
                    new_filter_name, has_changed = self.map_filter_name(filter_name, resource)
                    new_filter_value, value_changed = self.map_filter_value(filter_name, resource, filter_value)
                    updated_filters.append(f"{new_filter_name}={new_filter_value}")
                    changed = changed or has_changed or value_changed
                else:
                    changed = True
        self.add_static_required_filters(updated_filters, resource)
        return "&".join(updated_filters), changed

    def process_resource(self, resource_query, filter_key) -> bool:
        preprocess_filter = resource_query[filter_key].strip().replace(" & ", "__AND__").replace(" && ", "__ANDX2__")
        original_resource_name = resource_query["resourceType"]
        new_resource_name, resource_name_changed = self.map_resource_name(original_resource_name)
        resource_query["resourceType"] = new_resource_name
        filter_items = preprocess_filter.split("&")
        updated_filter, changed = self.process_filters(filter_items, original_resource_name)
        resource_query[filter_key] = updated_filter.replace("__AND__", " & ").replace("__ANDX2__", " && ")
        return changed or resource_name_changed

    def process_inner_join(self, query) -> bool:
        if query.get("_type") == "InnerJoin":
            has_changed = False
            for child in query["child"]:
                has_changed = has_changed or self.process_inner_join(child)
            return has_changed
        else:
            return self.process_resource(query, "fhirFilter")

    def process_basic_resource(self, resource: Any) -> bool:
        has_changed = self.process_resource(resource, "filterFhir")
        post_process_changed = self.post_process_basic_resource(resource)
        return post_process_changed or has_changed

    def process_group_resource(self, resource: Any, has_changed: List[bool]) -> bool:
        group_changed = self.post_process_group_resource(resource)
        return reduce(lambda x, y: x or y, has_changed, group_changed)

    T = TypeVar('T')

    def walk_query(
            self,
            query: Any,
            basic_resource_visitor: Callable[[Any], T],
            group_resource_visitor: Callable[[Any, List[T]], Optional[T]]
    ) -> Optional[T]:
        if "criteria" in query:
            group_criteria_expression_result = []
            for criteria in query["criteria"]:
                criteria_result = self.walk_query(criteria, basic_resource_visitor, group_resource_visitor)
                if criteria_result:
                    group_criteria_expression_result.append(criteria_result)
            return group_resource_visitor(query, group_criteria_expression_result)

        return basic_resource_visitor(query)

    def process_request(self, query) -> bool:
        if "request" in query:
            has_changed = self.walk_query(query["request"], self.process_basic_resource,
                                          self.process_group_resource) or False
            return has_changed
        return False

    def process_query(self, query, debug_path: Optional[Path] = None) -> Tuple[bool, bool]:
        """
        By default has_changed will be True even if there is no modification since we need to upgrade the version number
        Returns: A tuple has_changed, was_upgraded
        """
        if not query:
            return False, False

        # skip queries already updated
        query_version = query.get("version", None)
        if query_version == self.version_name:
            LOGGER.info("Skipping already updated query")
            return False, False
        elif self.previous_version_name is not None and query_version not in self.previous_version_name:
            LOGGER.info(
                f"Won't upgrade a query which is not from previous version (expected: {self.previous_version_name},"
                f" actual {self.version_name})")
            return False, False
        _type = query.get("_type", None)
        was_upgraded = False
        try:
            if "request" == _type:
                was_upgraded = self.process_request(query)
            elif "InnerJoin" == _type:
                was_upgraded = self.process_inner_join(query)
            elif "resource" == _type:
                was_upgraded = self.process_resource(query, "fhirFilter")
            else:
                raise ValueError(f"Unknown query type {_type}")

            query["version"] = self.version_name
        except Exception as e:
            LOGGER.error(f"Failed to process query {query}", exc_info=e)
            if debug_path:
                failed_path, _ = tempfile.mkstemp(dir=str(debug_path))
                with open(failed_path, "w") as fh:
                    json.dump(query, fh)
        # if the process failed then we don't want to save the changes
        return query.get("version", None) == self.version_name, was_upgraded

    def do_update_old_query_snapshots(self, queries: List[Any], save_query: Callable[[Any], None], dry_run, debug):
        error_loading = 0
        processed = 0
        upgraded = 0
        changed_queries = []
        debug_path: Optional[Path] = None
        versions_recap = {}
        if debug:
            debug_path = Path(tempfile.mkdtemp(prefix=f"update_{self.version_name}_"))
        for rqs in queries:
            try:
                query = json.loads(rqs.serialized_query)
                query_version = query.get("version", None)
            except Exception as e:
                error_loading += 1
                LOGGER.error("Could not load query %s", rqs.serialized_query, exc_info=e)
                continue
            has_changed, was_upgraded = self.process_query(query, debug_path)
            updated_query = json.dumps(query)
            new_query_version = self.version_name if has_changed else query_version
            versions_recap[new_query_version] = versions_recap.get(new_query_version, 0) + 1
            if has_changed:
                processed += 1
                if was_upgraded:
                    upgraded += 1
                    if debug:
                        LOGGER.info(f"Updating query from {rqs.serialized_query} to {updated_query}")
                        changed_queries.append({"before": rqs.serialized_query, "after": updated_query})
                rqs.serialized_query = updated_query
                if not dry_run:
                    save_query(rqs)
        LOGGER.info(f"Processed {processed} queries ({upgraded} upgraded)")
        LOGGER.info(f"Versions recap : {versions_recap}")
        if error_loading:
            LOGGER.warning(f"{error_loading} failed to load")
        if debug:
            with open(debug_path / "before", "w") as fh:
                json.dump([json.loads(c["before"]) for c in changed_queries], fh, indent=2)
            with open(debug_path / "after", "w") as fh:
                json.dump([json.loads(c["after"]) for c in changed_queries], fh, indent=2)

    def update_old_query_snapshots(self, dry_run: bool = True, debug: bool = True, with_filters: bool = True):
        LOGGER.info(f"Will update requests to version {self.version_name}. Dry run : {dry_run}")
        all_rqs: List[RequestQuerySnapshot] = RequestQuerySnapshot.objects.all()
        self.do_update_old_query_snapshots(all_rqs, lambda r: r.save(), dry_run, debug)
        if with_filters:
            self.update_old_filters(dry_run, debug)

    def save_filter(self, f: RequestQuerySnapshot, filters: List[FhirFilter]):
        for resource_filter in filters:
            if resource_filter.uuid == f.title:
                query = json.loads(f.serialized_query)
                resource_filter.query_version = query.get("version", self.version_name)
                resource_filter.filter = query["fhirFilter"]
                resource_filter.save()
                return

    def update_old_filters(self, dry_run: bool = True, debug: bool = True):
        LOGGER.info(f"Will update filters to version {self.version_name}. Dry run : {dry_run}")
        all_filters: List[FhirFilter] = FhirFilter.objects.all()
        self.do_update_old_query_snapshots([RequestQuerySnapshot(
            title=f.uuid,
            serialized_query=json.dumps({"version": f.query_version, "_type": "resource", "resourceType": f.fhir_resource, "fhirFilter": f.filter}))
            for
            f in all_filters], lambda r: self.save_filter(r, all_filters), dry_run, debug)

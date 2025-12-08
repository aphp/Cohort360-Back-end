import re
import urllib.parse
from typing import Iterable, Tuple

from cohort.models.fhir_filter import FhirFilter
from cohort.models.request_query_snapshot import RequestQuerySnapshot


def replace_in_filter_fhir_for_resource(json_str: str, resource_type: str, old_value: str, new_value: str) -> str:
    """
    Replace occurrences of `old_value` with `new_value` inside the `filterFhir` field
    of entries whose `resourceType` matches `resource_type`.
    """
    pattern = re.compile(
        rf'("resourceType"\s*:\s*"{re.escape(resource_type)}"[^}}]*?"filterFhir"\s*:\s*")([^"]*)(")',
        flags=re.DOTALL,
    )

    def _replacer(match: re.Match) -> str:
        before = match.group(1)
        content = match.group(2)
        after = match.group(3)
        new_content = content.replace(old_value, new_value)
        return before + new_content + after

    return pattern.sub(_replacer, json_str)


def get_all_queries_with_pattern(pattern: str) -> Iterable[RequestQuerySnapshot]:
    return RequestQuerySnapshot.objects.filter(serialized_query__contains=pattern)


def get_all_queries_with_multi_pattern(patterns: list) -> Iterable[RequestQuerySnapshot]:
    qs = RequestQuerySnapshot.objects.all()
    for pattern in patterns:
        qs = qs.filter(serialized_query__contains=pattern)
    return qs


def get_all_filter_fhir_with_pattern(pattern: str) -> Iterable[FhirFilter]:
    return FhirFilter.objects.filter(filter__contains=pattern)


def get_all_filter_fhir_with_resource_and_pattern(resource: str, pattern: str) -> Iterable[FhirFilter]:
    return FhirFilter.objects.filter(fhir_resource=resource, filter__contains=pattern)


def _encode_pair(old_value: str, new_value: str) -> Tuple[str, str]:
    """URL-encode a pair of values consistently.

    Returns (old_value_encoded, new_value_encoded).
    """
    return urllib.parse.quote(old_value), urllib.parse.quote(new_value)


def patch_query_by_resource(resource_type: str, old_value: str, new_value: str) -> None:
    filtered_queries = get_all_queries_with_multi_pattern(patterns=[resource_type, old_value])
    for query in filtered_queries:
        patched_query = replace_in_filter_fhir_for_resource(
            query.serialized_query, resource_type, old_value, new_value
        )
        if patched_query != query.serialized_query:
            query.serialized_query = patched_query
            print("Query patched: " + str(query.uuid))
            # Limit DB write to the changed field, while still triggering patch creation
            query.save(update_fields=["serialized_query"])


def patch_query(old_value: str, new_value: str) -> None:
    filtered_queries = get_all_queries_with_pattern(pattern=old_value)
    for query in filtered_queries:
        patched_query = query.serialized_query.replace(old_value, new_value)
        if patched_query != query.serialized_query:
            query.serialized_query = patched_query
            print("Query patched: " + str(query.uuid))
            query.save(update_fields=["serialized_query"])


def patch_filter(old_value: str, new_value: str) -> None:
    """Patch every FhirFilter containing old_value (URL-encoded) with new_value.

    Values are URL-encoded before replacement to match storage format.
    """
    old_value_encoded, new_value_encoded = _encode_pair(old_value, new_value)
    filtered_queries = get_all_filter_fhir_with_pattern(pattern=old_value_encoded)
    _patch_filter_queryset(filtered_queries, old_value_encoded, new_value_encoded)


def _patch_filter_queryset(
        filtered_queries: Iterable[FhirFilter],
        old_value_encoded: str,
        new_value_encoded: str,
) -> None:
    """Apply encoded replacement on an iterable of FhirFilter and save only when changed."""
    for filter_fhir_object in filtered_queries:
        patched_query = filter_fhir_object.filter.replace(old_value_encoded, new_value_encoded)
        if patched_query != filter_fhir_object.filter:
            filter_fhir_object.filter = patched_query
            print("filter patched: " + str(filter_fhir_object.uuid))
            filter_fhir_object.save(update_fields=["filter"])


def patch_filter_by_resource(fhir_resource: str, old_value: str, new_value: str) -> None:
    """Patch FhirFilter for a specific resource only (values URL-encoded)."""
    old_value_encoded, new_value_encoded = _encode_pair(old_value, new_value)
    filtered_queries = get_all_filter_fhir_with_resource_and_pattern(
        resource=fhir_resource,
        pattern=old_value_encoded,
    )
    _patch_filter_queryset(filtered_queries, old_value_encoded, new_value_encoded)

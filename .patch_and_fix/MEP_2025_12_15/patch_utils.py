import re
import urllib.parse
from collections import Counter
from typing import Iterable, Sequence, Tuple

from cohort.models.fhir_filter import FhirFilter
from cohort.models.request_query_snapshot import RequestQuerySnapshot

# Keep URL quoting rules centralized (same behavior everywhere).
_URL_QUOTE_SAFE = "~()*!.'"


def replace_in_filter_fhir_for_resource(
        json_str: str,
        resource_type: str,
        old_value: str,
        new_value: str,
) -> str:
    """
    Replace occurrences of `old_value` with `new_value` inside the `filterFhir` field
    of entries whose `resourceType` matches `resource_type`.

    Note: operates on the serialized JSON string via regex (no JSON parsing).
    """
    pattern = re.compile(
        rf'("resourceType"\s*:\s*"{re.escape(resource_type)}"[^}}]*?"filterFhir"\s*:\s*")([^"]*)(")',
        flags=re.DOTALL,
    )

    def _replacer(match: re.Match) -> str:
        before, content, after = match.group(1), match.group(2), match.group(3)
        return before + content.replace(old_value, new_value) + after

    return pattern.sub(_replacer, json_str)


def get_all_queries_with_pattern(pattern: str) -> Iterable[RequestQuerySnapshot]:
    return RequestQuerySnapshot.objects.filter(serialized_query__contains=pattern)


def get_all_queries_with_multi_pattern(patterns: Sequence[str]) -> Iterable[RequestQuerySnapshot]:
    qs = RequestQuerySnapshot.objects.all()
    for pattern in patterns:
        qs = qs.filter(serialized_query__contains=pattern)
    return qs


def get_all_filter_fhir_with_pattern(pattern: str) -> Iterable[FhirFilter]:
    return FhirFilter.objects.filter(filter__contains=pattern)


def get_all_filter_fhir_with_resource_and_pattern(resource: str, pattern: str) -> Iterable[FhirFilter]:
    return FhirFilter.objects.filter(fhir_resource=resource, filter__contains=pattern)


def encode(value: str) -> str:
    """
    URL-encode a value while keeping a fixed safe set.

    Special case preserved: if input contains '=' we only encode the part after the first '='.
    (This matches existing storage format expectations.)
    """
    if "=" in value:
        left, right = value.split("=", 1)
        return f"{left}={urllib.parse.quote(right, safe=_URL_QUOTE_SAFE)}"
    return urllib.parse.quote(value, safe=_URL_QUOTE_SAFE, encoding="utf-8", errors="replace")


def _encode_pair(old_value: str, new_value: str) -> Tuple[str, str]:
    """URL-encode a pair of values consistently.

    Returns (old_value_encoded, new_value_encoded).
    """
    return encode(old_value), encode(new_value)


def _print_counter_summary(counter: Counter) -> None:
    print(f"Ignorées        : {counter['ignored']}")
    print(f"Sans changement : {counter['unchanged']}")
    print(f"Patchées        : {counter['patched']}")


def patch_query_by_resource(resource_type: str, old_value: str, new_value: str) -> None:
    filtered_queries = get_all_queries_with_multi_pattern(patterns=[resource_type, old_value])
    total = filtered_queries.count()  # same intent as len(qs), but without materializing all rows
    print(f"Nombre de requêtes: {total}")

    loglist = Counter()
    for index, query in enumerate(filtered_queries, start=1):
        print(f"### {index}/{total} ###")

        if query.serialized_query is None:
            print("Query None")
            loglist["ignored"] += 1
            continue

        print(f"\nQuery: {query.uuid} - {query.owner}")
        patched_query = replace_in_filter_fhir_for_resource(
            query.serialized_query,
            resource_type,
            old_value,
            new_value,
        )

        if query.serialized_query == patched_query:
            print("Pas de changement")
            loglist["unchanged"] += 1
            continue

        query.serialized_query = patched_query
        print("Query patched")
        loglist["patched"] += 1
        query.save(update_fields=["serialized_query"])

    _print_counter_summary(loglist)


def patch_query(old_value: str, new_value: str) -> None:
    filtered_queries = get_all_queries_with_pattern(pattern=old_value)

    loglist = Counter()
    for query in filtered_queries:
        if query.serialized_query is None:
            # Keep behavior safe; previously this would crash on .replace
            print("Query None")
            loglist["ignored"] += 1
            continue

        patched_query = query.serialized_query.replace(old_value, new_value)
        if query.serialized_query == patched_query:
            print("Pas de changement")
            loglist["unchanged"] += 1
            continue

        query.serialized_query = patched_query
        print("Query patched: " + str(query.uuid))
        query.save(update_fields=["serialized_query"])
        loglist["patched"] += 1
    _print_counter_summary(loglist)


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
        if patched_query == filter_fhir_object.filter:
            continue

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

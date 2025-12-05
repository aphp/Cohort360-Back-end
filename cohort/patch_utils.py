import re

from cohort.models.request_query_snapshot import RequestQuerySnapshot
from django.db.models import QuerySet


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


def get_all_queries_with_pattern(pattern: str) -> QuerySet:
    return RequestQuerySnapshot.objects.filter(serialized_query__contains=pattern)


def patch_query_by_resource(resource_type: str, old_value: str, new_value: str) -> None:
    filtered_queries = get_all_queries_with_pattern(pattern=resource_type)
    for query in filtered_queries:
        patched_query = replace_in_filter_fhir_for_resource(
            query.serialized_query, resource_type, old_value, new_value
        )
        if patched_query != query.serialized_query:
            query.serialized_query = patched_query
            print("Query patched: " + str(query.uuid))
            query.save()


def patch_query(old_value: str, new_value: str) -> None:
    filtered_queries = get_all_queries_with_pattern(pattern=old_value)
    for query in filtered_queries:
        patched_query = query.serialized_query.replace(old_value, new_value)
        query.serialized_query = patched_query
        print("Query patched: " + str(query.uuid))
        query.save(update_fields=["serialized_query"])

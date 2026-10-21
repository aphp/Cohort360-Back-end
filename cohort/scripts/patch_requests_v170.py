import re
from urllib.parse import unquote

from cohort.scripts.patch_requests_v164 import NEW_VERSION as PREV_VERSION
from cohort.scripts.query_request_updater import QueryRequestUpdater

NEW_VERSION = "v1.7.0"

# BC3.3 : les analyses de biologie ne sont plus rattachées à une visite,
# les critères de visite (encounter.*, patientAge) n'ont plus de sens sur la Biologie.
BIOLOGY = "Observation"
ENCOUNTER_PARAM_RE = re.compile(r"\bencounter\.[A-Za-z0-9_\-]+")


def is_encounter_filter(filter_name: str, filter_value: str) -> bool:
    name = unquote(filter_name)
    if name.startswith("encounter."):
        return True
    # Option « inclure les valeurs nulles » : _filter=(encounter.period-start ge …) or not (encounter.period-start eq "*")
    return name == "_filter" and bool(ENCOUNTER_PARAM_RE.search(unquote(filter_value)))


def remove_patient_age(resource) -> bool:
    if resource.get("resourceType") != BIOLOGY or "patientAge" not in resource:
        return False
    return resource.pop("patientAge") is not None


FILTER_MAPPING = {}

FILTER_NAME_TO_SKIP = {BIOLOGY: [is_encounter_filter]}

FILTER_VALUE_MAPPING = {}

STATIC_REQUIRED_FILTERS = {}

RESOURCE_NAME_MAPPING = {}


updater_v170 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING,
    post_process_basic_resource=remove_patient_age,
)

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cohort_job_server.query_executor_api.enums import CriteriaType, ResourceType

if TYPE_CHECKING:
    from cohort_job_server.query_executor_api.schemas import CohortQuery, Criteria

logger = logging.getLogger(__name__)


# Procedure ne porte que du CCAM (EDS), donc un token sans système est du CCAM legacy.
CCAM_CODESYSTEMS = frozenset(
    {
        "https://www.atih.sante.fr/plateformes-de-transmission-et-logiciels/logiciels-espace-de-telechargement/id_lot/3550",
        "https://terminology.eds.aphp.fr/aphp-orbis-ccam",
        "https://aphp.fr/ig/fhir/core/CodeSystem/CCAMDescriptiveVerAPHP",
    }
)


def prefix_ccam_leaf_code(token: str) -> str:
    # Le référentiel CCAM a été ré-encodé (segmentation des actes, suffixe de niveau sur les
    # noeuds) : un code stocké ne matche plus à l'identique, quel que soit son format. On le
    # cherche donc en préfixe, sauf s'il porte déjà un `*` ou un système non-CCAM.
    system, sep, code = token.rpartition("|")
    if sep and system not in CCAM_CODESYSTEMS:
        return token
    if not code or code.endswith("*"):
        return token
    return f"{system}{sep}{code}*"


def add_prefix_search_on_ccam_leaves(filter_fhir: str, resource_type: ResourceType) -> str:
    if not filter_fhir or resource_type != ResourceType.PROCEDURE:
        return filter_fhir
    params = []
    for param in filter_fhir.split("&"):
        key, sep, value = param.partition("=")
        base, _, modifier = key.partition(":")
        # `code:in` / `code:not-in` portent une URI de ValueSet, pas des codes : on ne les touche pas.
        if sep and base == "code" and modifier in ("", "not"):
            value = ",".join(prefix_ccam_leaf_code(token) for token in value.split(","))
        params.append(f"{key}{sep}{value}")
    return "&".join(params)


class QueryFormatter:
    """The SJS translates `filterFhir` to Solr itself: Django only adds what the SJS doesn't do (CCAM prefix)."""

    @staticmethod
    def format(cohort_query: CohortQuery) -> Criteria | None:
        def format_criteria(criteria: Criteria) -> Criteria | None:
            if criteria is None:
                return None
            if criteria.criteria_type == CriteriaType.BASIC_RESOURCE:
                criteria.filter_fhir = add_prefix_search_on_ccam_leaves(criteria.filter_fhir, criteria.resource_type)
                return criteria
            for sub_criteria in criteria.criteria:
                format_criteria(sub_criteria)
            return criteria

        return format_criteria(cohort_query.criteria)

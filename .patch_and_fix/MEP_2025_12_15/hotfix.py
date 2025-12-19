import json
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone
from collections import Counter

from accesses.models import Access, Perimeter
from accesses_perimeters.apps import AccessesPerimetersConfig
from accesses_perimeters.models import CareSiteMapperMep, ListCohort
from admin_cohort.models.user import User
from admin_cohort.types import JobStatus
from cohort.models import Folder, RequestQuerySnapshot
from cohort.models.cohort_result import CohortResult
from cohort.models.dated_measure import DatedMeasure
from cohort.models.request import Request

"""
Hotfix de restauration de cohortes (incident de rollout).

Contexte
--------
Suite à une erreur de rollout, les bases de production ont été écrasées par celles de préproduction.
Cet écrasement a entraîné la perte de cohortes et des objets applicatifs associés.

But
---
Ce script vise à recréer les cohortes perdues à partir des données disponibles côté OMOP (ListCohort),
en reconstruisant avec des noms par défaut :
- les cohortes (CohortResult) perdues,
- les requêtes (Request) associées,
- les snapshots de requêtes (RequestQuerySnapshot),
- les dossiers (Folder),
- les mesures datées (DatedMeasure).

Point d’entrée
--------------
- `patch_cohorts(date_input_limit, specify_user=None)` : restaure les cohortes à partir des ListCohort
  insérées depuis `date_input_limit` (optionnellement pour un utilisateur spécifique).

Remarques
---------
- Le traitement est conçu pour être idempotent : si une cohorte existe déjà pour un group_id donné,
  elle est ignorée.
- Chaque création est encapsulée dans une transaction, et les erreurs sont loguées sans interrompre
  le traitement global.
- Il est nécessaire de créer sur le PG de prod une table de mapping entre les list_id des cohortes virtuelles 
  de pre prod et prod avec leur care_site_id correspondant -> 'omop.caresite_mapper_mep'. 
"""


def _debug(msg: str, owner: Optional[str] = None) -> None:
    """Simple console logger for this hotfix script (kept intentionally minimal)."""
    if owner:
        print(f"[hotfix.patch][{owner}] {msg}")
    else:
        print(f"[hotfix.patch] {msg}")


def get_old_to_new_prod_mapping_from_model() -> Dict[int, int]:
    """
    Build a mapping `{old_prod_b_id -> new_prod_a_id}` from OMOP `caresite_mapper_mep`.

    Defensive behavior:
    - skips rows with missing ids
    - ensures the `care_site_id` exists as a Perimeter
    - if `new_prod_a_id` doesn't match any Perimeter.cohort_id, falls back to the perimeter cohort_id
      of the referenced `care_site_id` (same behavior as before).
    """
    db_alias = AccessesPerimetersConfig.DB_ALIAS
    sql = """
          SELECT *
          FROM omop.caresite_mapper_mep;
          """

    mapping: Dict[int, int] = {}
    _debug("Start mapping care_site_id to new_prod_a_id")

    for row in CareSiteMapperMep.objects.using(db_alias).raw(sql):
        old_id = getattr(row, "old_prod_b_id", None)
        care_site_id = getattr(row, "care_site_id", None)
        new_id = getattr(row, "new_prod_a_id", None)

        if old_id is None or new_id is None or care_site_id is None:
            continue

        if not Perimeter.objects.filter(pk=care_site_id).exists():
            continue

        if not Perimeter.objects.filter(cohort_id=new_id).exists():
            _debug(f"WARN invalid row: new_id={new_id!r} has no cohort_id")
            perimeter = Perimeter.objects.get(pk=care_site_id)
            id_perimeter = perimeter.cohort_id
            if id_perimeter is None:
                _debug("WARN: id_perimeter is not defined")
                continue
            new_id = id_perimeter

        mapping[int(old_id)] = int(new_id)

    _debug("End mapping care_site_id to new_prod_a_id")
    return mapping


def is_valid_perimeter_in_user_accesses(perimeter, owner: str) -> bool:
    """
    Check whether a user has a valid access on a given perimeter (directly or via above_levels).
    """
    if perimeter is None:
        return False
    accesses = Access.objects.filter(profile__user__pk=owner).all()
    for access in accesses:
        if access.perimeter is None:
            continue
        if (access.perimeter.id == perimeter.id or access.perimeter.id in perimeter.above_levels) and access.is_valid:
            _debug(f"Access granted for user {owner} on perimeter {perimeter.id}", owner)
            return True
    return False


def _get_owner_from_user_aph_id(user_aph_id: str) -> User:
    """
    Resolve the cohort owner from an AHP identifier.
    Tries `pk`, then `username` (kept as-is to preserve current behavior).
    """
    try:
        return User.objects.get(pk=user_aph_id)
    except User.DoesNotExist:
        pass

    try:
        return User.objects.get(username=user_aph_id)
    except User.DoesNotExist as e:
        raise ValueError(f"No User found for user_aph_id={user_aph_id}") from e


def _retrieve_perimeters_hotfix(json_query: str) -> List[str]:
    """
    Extract `sourcePopulation.caresiteCohortList` from the JSON query and normalize to `List[str]`.

    Accepts:
    - ints
    - numeric strings
    """
    try:
        query = json.loads(json_query)
        perimeters_ids = query["sourcePopulation"]["caresiteCohortList"]

        if not isinstance(perimeters_ids, list):
            raise TypeError("caresiteCohortList must be a list")

        normalized: List[str] = []
        for item in perimeters_ids:
            if isinstance(item, int):
                normalized.append(str(item))
            elif isinstance(item, str) and item.isnumeric():
                normalized.append(item)
            else:
                raise ValueError(f"Invalid perimeter id: {item!r}")

        return normalized
    except (json.JSONDecodeError, TypeError, KeyError, ValueError) as e:
        raise ValueError(f"Error extracting perimeters ids from JSON query - {e}") from e


def _get_practitioner_patient_lists_since(since_dt: str, specify_user: Optional[str] = None):
    """
    Fetch ListCohort rows from OMOP matching:
    - Practitioner -> Patient
    - inserted since `since_dt`
    - not deleted
    - non empty
    Optionally filters by `_sourcereferenceid` when `specify_user` is provided.
    """
    default_where = f" AND _sourcereferenceid = '{specify_user}'" if specify_user else ""
    _debug(f"default_where is: {default_where})")
    db_alias = AccessesPerimetersConfig.DB_ALIAS

    sql = f"""
              SELECT *
              FROM omop.list
              WHERE source__type = 'Practitioner'
                AND subject__type = 'Patient'
                AND insert_datetime >= '{since_dt}'
                AND delete_datetime IS NULL
                AND _size > 0 {default_where};
              """
    return ListCohort.objects.using(db_alias).raw(sql)


def map_perimeters_ids_to_new_prod_ids(
        mapping: Dict[int, int],
        perimeters_ids: List[str],
        owner: Optional[str] = None,
) -> Optional[List[str]]:
    """
    Map OMOP/old perimeter ids to the new prod ids using `mapping`.
    Returns `None` when nothing could be mapped (matches existing behavior).
    """
    mapped: List[str] = []

    for raw_id in perimeters_ids:
        try:
            old_id = int(raw_id)
        except (TypeError, ValueError):
            _debug(f"WARN invalid perimeter id (cannot cast to int): {raw_id!r}", owner)
            continue

        new_id = mapping.get(old_id)
        if new_id is None:
            _debug(f"WARN perimeter id not found in mapping: {old_id!r}", owner)
            continue

        mapped.append(str(new_id))

    _debug(f"mapped perimeters ids: {mapped}")
    if len(mapped) != len(perimeters_ids):
        _debug(f"WARN some perimeters ids were not mapped: {set(perimeters_ids) - set(mapped)}", owner)
    elif len(mapped) == 0:
        _debug(f"ERROR no perimeters ids were mapped: {perimeters_ids}", owner)
        return None

    return mapped


def patch_cohorts(date_input_limit: str, specify_user: Optional[str] = None) -> None:
    """
    Hotfix script: recreate CohortResult + Request + RequestQuerySnapshot + DatedMeasure
    from OMOP ListCohort rows since `date_input_limit`.

    Important:
    - keeps idempotency by skipping `group_id` already existing
    - runs each cohort creation in its own `transaction.atomic()`
    - logs errors and continues for next items (same behavior as before)
    """
    _debug(f"START patch(date_input_limit={date_input_limit!r})")
    mapping = get_old_to_new_prod_mapping_from_model()

    list_listcohort = _get_practitioner_patient_lists_since(date_input_limit, specify_user)
    _debug(f"ListCohort fetched: count={len(list_listcohort)}")
    if not list_listcohort:
        _debug(f"No ListCohort found -> raising ValueError (date_input_limit={date_input_limit!r})")
        raise ValueError(f"No ListCohort found since date_input_limit={date_input_limit!r}")

    count = len(list_listcohort)
    error_list: List[str] = []

    for idx, list_cohort in enumerate(list_listcohort, start=1):
        _debug(f"Processing ListCohort #{idx}/{count}")
        _debug(
            "Using first ListCohort: "
            f"\nid={getattr(list_cohort, 'id', None)!r}, "
            f"\ninsert_datetime={getattr(list_cohort, 'insert_datetime', None)!r}, "
            f"\n_sourcereferenceid={getattr(list_cohort, '_sourcereferenceid', None)!r}, "
            f"\n_size={getattr(list_cohort, '_size', None)!r}"
        )

        user_aph_id = specify_user if specify_user else list_cohort._sourcereferenceid
        cohort_date = str(list_cohort.insert_datetime)[0:16].strip()
        cohort_group_id = list_cohort.id
        cohort_json_query = list_cohort.note_query_text

        _debug(f"cohort_date={cohort_date!r}")
        _debug(f"cohort_group_id={cohort_group_id!r}")
        _debug(
            f"cohort_json_query: type={type(cohort_json_query).__name__}, "
            f"length={len(cohort_json_query) if cohort_json_query else 0}"
        )

        cohort_user = _get_owner_from_user_aph_id(user_aph_id=user_aph_id)
        _debug(
            f"Resolved owner user: id={getattr(cohort_user, 'pk', None)!r}, "
            f"username={getattr(cohort_user, 'username', None)!r}"
        )

        cohort_name = f"Cohorte du {cohort_date}"
        cohort_description = f"Cohorte de récupération de l'utilisateur: {cohort_user}, créée le {cohort_date}"
        cohort_size = list_cohort._size

        _debug(
            f"cohort_name={cohort_name!r}"
            f"\ncohort_description={cohort_description!r}"
            f"\ncohort_size={cohort_size!r}",
            user_aph_id,
        )

        existing = (
            CohortResult.objects.filter(group_id=str(cohort_group_id))
            .order_by("-pk")
            .first()
        )
        if existing:
            error_list.append(
                f"cohort_group_id: {cohort_group_id} is already created : "
                f"{existing.name} - {existing.owner} - {existing.created_at}"
            )
            _debug(
                "go to next CR... CohortResult already exists for this group_id -> "
                "\nskipping creation steps in transaction.atomic(): "
                f"\ngroup_id: {existing.group_id} - owner: {existing.owner} "
                f"\npk={getattr(existing, 'pk', None)!r}, uuid={getattr(existing, 'uuid', None)!r}, "
                f"\ngroup_id={getattr(existing, 'group_id', None)!r}",
                user_aph_id,
            )
            continue

        with transaction.atomic():
            _debug("Getting/Creating Folder ...", user_aph_id)

            perimeters_ids = map_perimeters_ids_to_new_prod_ids(
                mapping,
                _retrieve_perimeters_hotfix(json_query=cohort_json_query),
                owner=user_aph_id,
            )
            if perimeters_ids is None:
                _debug("ERROR: Abort cohort creation, no perimeters ids mapped -> raising ValueError", user_aph_id)
                error_list.append(f"cohort_group_id: {cohort_group_id} no perimeters ids mapped")
                continue

            # Only for get an alert on user - it was chosen to create cohort instead accesses are not provided
            for pid in perimeters_ids:
                _debug(f"perimeters_ids: {pid}", user_aph_id)
                perimeter = Perimeter.objects.filter(cohort_id=pid).first()
                if not is_valid_perimeter_in_user_accesses(perimeter, user_aph_id):
                    _debug(
                        f"ERROR: Abort cohort creation, access denied for user {user_aph_id} on perimeter {pid}",
                        user_aph_id,
                    )
                    if perimeter is not None:
                        error_list.append(
                            f"cohort_group_id: {cohort_group_id} access denied for user {user_aph_id} "
                            f"on perimeter care site id: {perimeter.id} - cohort_id:{pid} "
                        )
                    else:
                        error_list.append(
                            f"cohort_group_id: {cohort_group_id} access denied for user {user_aph_id} "
                            f"on perimeter cohort_id:{pid} (no Perimeter found)"
                        )

            perimeters_len = len(perimeters_ids)
            _debug(
                f"perimeters_ids computed: type={type(perimeters_ids).__name__}, "
                f"len={perimeters_len}, value={perimeters_ids!r}",
                user_aph_id,
            )

            folder_name = "Cohortes postérieures au 2025-07-21"
            folder_description = "Projet créé par des cohortes générées après le 2025-07-21"
            folder, created = Folder.objects.get_or_create(
                owner=cohort_user,
                name=folder_name,
                defaults={"description": folder_description},
            )
            if created:
                _debug(
                    f"Folder created: pk={getattr(folder, 'pk', None)!r}, uuid={getattr(folder, 'uuid', None)!r}, "
                    f"name={getattr(folder, 'name', None)!r}",
                    user_aph_id,
                )
            else:
                _debug(
                    f"Folder found: pk={getattr(folder, 'pk', None)!r}, uuid={getattr(folder, 'uuid', None)!r}, "
                    f"name={getattr(folder, 'name', None)!r}",
                    user_aph_id,
                )

            req = Request.objects.create(
                owner=cohort_user,
                parent_folder=folder,
                name=f"Nouvelle requête n ({cohort_name})",
                description=f"Request issue de la cohorte ({cohort_name})",
            )
            _debug(
                f"Request created: pk={getattr(req, 'pk', None)!r}, uuid={getattr(req, 'uuid', None)!r}, "
                f"name={getattr(req, 'name', None)!r}",
                user_aph_id,
            )

            rqs = RequestQuerySnapshot.objects.create(
                owner=cohort_user,
                request=req,
                serialized_query=cohort_json_query,
                perimeters_ids=perimeters_ids,
                version=1,
                name=cohort_name,
            )
            _debug(
                f"RequestQuerySnapshot created: pk={getattr(rqs, 'pk', None)!r}, uuid={getattr(rqs, 'uuid', None)!r}, "
                f"version={getattr(rqs, 'version', None)!r}",
                user_aph_id,
            )

            now = timezone.now()
            _debug(f"Creating DatedMeasure ... fhir_datetime={now!r}", user_aph_id)
            dm = DatedMeasure.objects.create(
                owner=cohort_user,
                request_query_snapshot=rqs,
                fhir_datetime=now,
                measure=cohort_size,
                measure_min=cohort_size,
                measure_max=cohort_size,
                request_job_status=JobStatus.finished,
            )
            _debug(
                f"DatedMeasure created: pk={getattr(dm, 'pk', None)!r}, uuid={getattr(dm, 'uuid', None)!r}, "
                f"measure={getattr(dm, 'measure', None)!r}",
                user_aph_id,
            )

            cohort_result = CohortResult.objects.create(
                owner=cohort_user,
                name=cohort_name,
                group_id=str(cohort_group_id),
                request_query_snapshot=rqs,
                dated_measure=dm,
                description=cohort_description,
                request_job_status=JobStatus.finished,
            )
            _debug(
                f"CohortResult created: pk={getattr(cohort_result, 'pk', None)!r}, "
                f"uuid={getattr(cohort_result, 'uuid', None)!r}, "
                f"group_id={getattr(cohort_result, 'group_id', None)!r}",
                user_aph_id,
            )

    _debug("END patch()")
    for error in error_list:
        _debug(error)
    return


# Command to run
# patch_cohorts("2025-07-21")  # Date from last MEP with switch prod a / prod b

# PATCH PERIMETERS IN REQUESTQUERYSNAPSHOT
def _remap_perimeters_in_json_query(request_query_snapshot: RequestQuerySnapshot, owner: Optional[str] = None):
    """
    À partir d'un `json_query` et d'un mapping ancien_id -> nouvel_id, remplace les ids
    trouvés dans `sourcePopulation.caresiteCohortList` par les nouveaux ids.

    Sécurités :
    - si `json_query` est vide ou None : log et return None
    - si `mapping` est vide ou None : log et return None
    - si le JSON est invalide ou ne contient pas la clé attendue : log et return None
    - si aucun id n'est mappé : log et return None

    Retourne :
    - None si rien n'a pu être mappé / modifié
    - sinon `(nouveau_json_query, nouvelle_liste_de_perimetres_ids_str)`
    """
    json_query = request_query_snapshot.serialized_query
    perimeters_ids = request_query_snapshot.perimeters_ids
    if not json_query:
        _debug("WARN _remap_perimeters_in_json_query called with empty json_query", owner)
        return None
    if not perimeters_ids:
        _debug("WARN _remap_perimeters_in_json_query called with empty perimeters_ids", owner)
        return None
    new_perimeters_ids = []
    for id in perimeters_ids:
        perimeter = Perimeter.objects.filter(cohort_id=id).first()
        if perimeter:
            new_perimeters_ids.append(id)
            continue
        _debug(f"WARN perimeter with cohort_id {id} is not define", owner)
        cohort = CohortResult.objects.filter(group_id=id).first()
        if cohort:
            new_perimeters_ids.extend(cohort.request_query_snapshot.perimeters_ids)
            continue
        _debug(f"WARN cohort with group_id {id} is not define", owner)
        return None
    _debug(f"old perimeters_ids: {json_query[78:125]}", owner)
    try:
        query_dict = json.loads(json_query)
    except json.JSONDecodeError as e:
        _debug(f"ERROR invalid JSON in json_query: {e}", owner)
        return None
    try:
        source_pop = query_dict.setdefault("sourcePopulation", {})
        source_pop["caresiteCohortList"] = [int(pid) for pid in new_perimeters_ids]
    except Exception as e:  # garde-fou, on ne veut pas faire planter un hotfix
        _debug(f"ERROR while injecting new perimeters into json_query: {e}", owner)
        return None
    try:
        new_json_query = json.dumps(query_dict)
    except TypeError as e:
        _debug(f"ERROR while dumping updated json_query: {e}", owner)
        return None
    _debug(f"_remap_perimeters_in_json_query: new={new_perimeters_ids!r}", owner)
    return new_json_query, new_perimeters_ids


def patch_request_source_population(user_aph: str = None) -> None:
    _debug(
        f"START patch_request_source_population Single User Mode {user_aph}" if user_aph else "START patch_request_source_population"
    )
    all_request_to_patch = (
        RequestQuerySnapshot.objects.filter(name__contains="Cohorte du 2025")
        .filter(owner_id=user_aph)
        .all()
        if user_aph
        else RequestQuerySnapshot.objects.filter(name__contains="Cohorte du 2025").all()
    )
    total = all_request_to_patch.count()
    _debug(f"RequestQuerySnapshot to patch: count={total}")
    skipped_reasons = Counter()
    for idx, rqs in enumerate(all_request_to_patch, start=1):
        _debug(
            f"[{idx}/{total}] Patching RequestQuerySnapshot pk={getattr(rqs, 'pk', None)!r}, "
            f"\nname={getattr(rqs, 'name', None)!r}"
        )
        json_query = rqs.serialized_query
        if not json_query:
            _debug(f"WARN serialized_query is empty -> skipping request {rqs.pk}", rqs.owner)
            skipped_reasons["skipped"] += 1
            skipped_reasons["empty_serialized_query"] += 1
            continue
        remap_result = _remap_perimeters_in_json_query(rqs, owner=getattr(rqs.owner, "pk", None))
        if remap_result is None:
            _debug("WARN nothing remapped for this RequestQuerySnapshot -> skipping save", rqs.owner)
            skipped_reasons["skipped"] += 1
            skipped_reasons["remap_failed"] += 1
            continue
        new_json_query, new_perimeters_ids = remap_result
        new_json_query = new_json_query.replace(": ", ":").replace(", ", ",")
        if new_json_query == json_query:
            _debug("INFO json_query unchanged after remap -> skipping save", rqs.owner)
            skipped_reasons["skipped"] += 1
            skipped_reasons["json_unchanged"] += 1
            continue
        rqs.serialized_query = new_json_query
        rqs.perimeters_ids = new_perimeters_ids
        rqs.save(update_fields=["serialized_query", "perimeters_ids", "modified_at"])
        skipped_reasons["patched"] += 1
        _debug("RequestQuerySnapshot patched successfully", rqs.owner)
    _debug(
        "END patch_request_source_population "
        f"\n- patched={skipped_reasons.get('patched', 0)}"
        f"\n- skipped={skipped_reasons.get('skipped', 0)}"
        f"\n  * empty_serialized_query={skipped_reasons.get('empty_serialized_query', 0)}"
        f"\n  * remap_failed={skipped_reasons.get('remap_failed', 0)}"
        f"\n  * json_unchanged={skipped_reasons.get('json_unchanged', 0)}"
        f"\n- total={total}"
    )

#patch_request_source_population()

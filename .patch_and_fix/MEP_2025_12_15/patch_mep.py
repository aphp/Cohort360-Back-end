from cohort.patch_utils import *


"""
Patch MEP (mise en production) — migration des requêtes et filtres sauvegardés.

Objectif
--------
Ce script applique des correctifs sur les objets persistés (requêtes et filtres)
afin de garantir la compatibilité après une MEP, en particulier :

- la mise à jour des anciennes requêtes (RequestQuerySnapshot / requêtes sauvegardées)
- la mise à jour des anciens filtres sauvegardés

Contexte
--------
Ces patchs sont nécessaires suite :
- aux changements de structure et/ou de champs sur les tables PMSI,
- aux évolutions de terminologie (renommage de paramètres, changement d’URLs de CodeSystem/StructureDefinition),
- aux évolutions des endpoints `_source` (ex. AREM / ORBIS).

Principe
--------
Les fonctions utilitaires importées depuis `cohort.patch_utils` effectuent des remplacements
ciblés dans :
- les requêtes sauvegardées (via `patch_query*`)
- les filtres sauvegardés (via `patch_filter*`)

Le script est organisé par ressource FHIR (ex. Condition, Procedure), puis par type de
modification :
- correction des valeurs de `_source`
- renommage de paramètres (ex. `recorded-date` -> `onset-date`)
- mapping d’URLs de terminologies (dictionnaire `mappings`)

Attention / Exploitation
------------------------
- Ce script est prévu pour être exécuté ponctuellement lors d’une MEP.
- Il n’est pas idempotent par conception si les remplacements ne sont pas strictement uniques
  (à vérifier avant relance).
- Toujours valider sur un environnement de recette/staging et/ou faire un backup avant exécution.
"""


# Condition
## SOURCE
### AREM
patch_query_by_resource("Condition", "_source=AREM", "_source=https://aphp.fr/ig/fhir/eds/Endpoint/arem")
filtered_queries = get_all_queries_with_multi_pattern(patterns=["Condition", "_source=AREM", ])
patch_filter_by_resource("Condition", "_source=AREM", "_source=https://aphp.fr/ig/fhir/eds/Endpoint/arem")
### ORBIS
patch_query_by_resource("Condition", "_source=ORBIS", "_source=https://dedalus.com/Orbis")
patch_filter_by_resource("Condition", "_source=ORBIS", "_source=https://dedalus.com/Orbis")
## RECORDED DATE
patch_query_by_resource("Condition", "recorded-date=", "onset-date=")
patch_filter_by_resource("Condition", "recorded-date=", "onset-date=")
## ORBIS STATUS
patch_query_by_resource("Condition", "orbis-status=", "diagnosisType=")
patch_filter_by_resource("Condition", "orbis-status=", "diagnosisType=")
# Procedure
## SOURCE
### AREM
patch_query_by_resource("Procedure", "_source=AREM", "_source=https://aphp.fr/ig/fhir/eds/Endpoint/arem")
patch_filter_by_resource("Procedure", "_source=AREM", "_source=https://aphp.fr/ig/fhir/eds/Endpoint/arem")
### ORBIS
patch_query_by_resource("Procedure", "_source=ORBIS", "_source=https://dedalus.com/Orbis")
patch_filter_by_resource("Procedure", "_source=ORBIS", "_source=https://dedalus.com/Orbis")

# URLS
mappings = {
    "https://terminology.eds.aphp.fr/fhir/StructureDefinition/orbis-status": "https://terminology.eds.aphp.fr/fhir/StructureDefinition/DiagnosisType",
    "https://terminology.eds.aphp.fr/aphp-orbis-patient-genre": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-patient-genre",
    "https://terminology.eds.aphp.fr/aphp-orbis-visit-type-admission": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-visit-type-admission",
    "https://terminology.eds.aphp.fr/aphp-orbis-visit-motif-admission": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-visit-motif-admission",
    "https://terminology.eds.aphp.fr/aphp-orbis-visit-destination": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-visit-destination",
    "https://terminology.eds.aphp.fr/aphp-orbis-visit-mode-entree": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-visit-mode-entree",
    "https://terminology.eds.aphp.fr/aphp-orbis-visit-mode-sortie": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-visit-mode-sortie",
    "https://terminology.eds.aphp.fr/aphp-orbis-visit-type-sortie": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-visit-type-sortie",
    "https://terminology.eds.aphp.fr/aphp-orbis-visite-status": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-visite-status",
    "https://terminology.eds.aphp.fr/aphp-orbis-visit-provenance": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-visit-provenance",
    "https://terminology.eds.aphp.fr/aphp-orbis-type-sejour": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-type-sejour",
    "https://terminology.eds.aphp.fr/aphp-orbis-visit-type": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-visit-type",
    "https://terminology.eds.aphp.fr/aphp-itm-anabio": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-itm-anabio",
    "https://terminology.eds.aphp.fr/aphp-itm-loinc": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-itm-loinc",
    "https://terminology.eds.aphp.fr/aphp-orbis-medicament-voie-administration": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-medicament-voie-administration",
    "https://terminology.eds.aphp.fr/atc": "https://terminology.eds.aphp.fr/fhir/CodeSystem/atc",
    "https://terminology.eds.aphp.fr/aphp-orbis-medicament-atc-article": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-medicament-atc-article",
    "https://terminology.eds.aphp.fr/aphp-medicament-type-prescription": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-medicament-type-prescription",
    "https://terminology.eds.aphp.fr/smt-medicament-ucd": "https://terminology.eds.aphp.fr/fhir/CodeSystem/smt-medicament-ucd",
    "https://smt.esante.gouv.fr/terminologie-cim-10/": "https://terminology.eds.aphp.fr/fhir/CodeSystem/itm-cim10",
    "https://terminology.eds.aphp.fr/aphp-orbis-condition-status": "https://terminology.eds.aphp.fr/fhir/CodeSystem/DiagnosisType",
    "https://terminology.eds.aphp.fr/aphp-orbis-ghm": "https://terminology.eds.aphp.fr/fhir/CodeSystem/aphp-orbis-ghm",
}

for old, new in mappings.items():
    print(f"Patching: {old} -> {new}")
    patch_query(old, new)
    print("Request Query Snapshot patched")
    patch_filter(old, new)
    print("Filter patched")

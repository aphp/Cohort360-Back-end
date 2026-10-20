import json
from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accesses.models import Perimeter, Access
from accesses.services.accesses import accesses_service
from accesses_fhir_perimeters.perimeters_updater import apply_perimeters_sync, compute_perimeters_sync, PerimetersSyncAborted, SYNCED_FIELDS


class Command(BaseCommand):
    help = (
        "Compare les périmètres construits depuis les Organization FHIR avec la table Perimeter. "
        "--dry-run affiche le rapport sans rien modifier, --apply applique ensuite exactement ce qui a été affiché"
    )

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true", help="Affiche le rapport sans rien écrire")
        mode.add_argument("--apply", action="store_true", help="Affiche le rapport puis applique la synchro")
        parser.add_argument("--output", help="Écrit le détail complet (JSON) dans ce fichier")
        parser.add_argument("--sample", type=int, default=10, help="Nombre d'exemples affichés par catégorie")

    def handle(self, *args, **options):
        try:
            sync, unchanged = compute_perimeters_sync()
        except PerimetersSyncAborted as e:
            raise CommandError(str(e))

        existing = {p.id: p for p in Perimeter.objects.all(even_deleted=True)}
        field_diffs = []
        for perimeter in sync.to_update:
            current = existing[perimeter.id]
            for f in SYNCED_FIELDS:
                if getattr(perimeter, f) != getattr(current, f):
                    field_diffs.append({"id": perimeter.id, "field": f, "current": str(getattr(current, f)), "fhir": str(getattr(perimeter, f))})
        accesses_on_deleted = Access.objects.filter(accesses_service.q_access_is_valid(), perimeter_id__in=sync.to_delete_ids)
        accesses_per_deleted = Counter(accesses_on_deleted.values_list("perimeter_id", flat=True))
        active_count = Perimeter.objects.all().count()
        sample = options["sample"]

        self.stdout.write(f"Racine: {settings.ROOT_PERIMETER_ID} - périmètres actifs en base: {active_count}")
        self.stdout.write(f"Inchangés: {len(unchanged)}")
        self.stdout.write(f"À créer: {len(sync.to_create)} - ex: {[(p.id, p.type_source_value, p.name) for p in sync.to_create[:sample]]}")
        self.stdout.write(f"À mettre à jour: {len(sync.to_update)} (dont réactivés: {len(sync.reactivated_ids)})")
        for f, count in Counter(d["field"] for d in field_diffs).most_common():
            examples = [(d["id"], d["current"], d["fhir"]) for d in field_diffs if d["field"] == f][:sample]
            self.stdout.write(f"  - {f}: {count} - ex (id, actuel, FHIR): {examples}")
        self.stdout.write(
            f"À supprimer: {len(sync.to_delete_ids)} ({len(sync.to_delete_ids) / active_count if active_count else 0:.1%} des périmètres actifs) "
            f"- accès valides qui seraient fermés: {sum(accesses_per_deleted.values())} "
            f"sur {len(accesses_per_deleted)} périmètres - ex: {sync.to_delete_ids[:sample]}"
        )
        self.stdout.write(f"Orphelins ignorés (non rattachés à la racine): {len(sync.orphans_ids)} - ex: {sync.orphans_ids[:sample]}")

        if output := options["output"]:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "to_create": [
                            {"id": p.id, "parent_id": p.parent_id, "type_source_value": p.type_source_value, "name": p.name} for p in sync.to_create
                        ],
                        "field_diffs": field_diffs,
                        "reactivated_ids": sync.reactivated_ids,
                        "to_delete_ids": sync.to_delete_ids,
                        "valid_accesses_on_deleted": {str(k): v for k, v in accesses_per_deleted.items()},
                        "orphans_ids": sync.orphans_ids,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            self.stdout.write(f"Détail écrit dans {output}")

        if options["apply"]:
            apply_perimeters_sync(sync)
            self.stdout.write("Synchro appliquée")

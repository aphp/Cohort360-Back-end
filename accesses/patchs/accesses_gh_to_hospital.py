from accesses.models import Perimeter
from accesses.tools.accesses_update import create_children_perimeters_accesses

"""
PATCH DU 6 DEC 2022
A pour but d'attribuer un accès hopital pour les accès sur les GH.
patch précédant la mise à jour GHU des périmètres sur OMOP.
"""
level_source = "Groupe hospitalier (GH)"
# Récupération des périmètres GH
perimeters_gh = Perimeter.objects.filter(type_source_value=level_source)

create_children_perimeters_accesses(perimeters_gh)

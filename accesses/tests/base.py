from typing import List

from django.db.models import Model, Manager, Field

from accesses.models import Perimeter
from admin_cohort.tools.tests_tools import ViewSetTests

"""
                                            APHP
                 ____________________________|____________________________
                 |                           |                           |
                 P0                          P1                          P2
       __________|__________          _______|_______          __________|__________
       |         |         |          |             |          |         |         |
       P3        P4       P5          P6            P7       P8          P9       P10
           ______|_______                                                    ______|_______
           |            |                                                    |            |
           P1 1         P12                                                  P13          P14
"""

PERIMETERS_DATA = [
    {'id': 1, 'name': 'APHP', 'source_value': 'APHP', 'short_name': 'AP-HP',
     'local_id': 'Local 00', 'type_source_value': 'AP-HP', 'parent_id': None, 'level': 1},
    {'id': 2, 'name': 'P0', 'source_value': 'P0', 'short_name': 'P0',
     'local_id': 'Local P0', 'type_source_value': 'Groupe hospitalier (GH)', 'parent_id': 1, 'level': 2},
    {'id': 3, 'name': 'P1', 'source_value': 'P1', 'short_name': 'P1',
     'local_id': 'Local P1', 'type_source_value': 'Groupe hospitalier (GH)', 'parent_id': 1, 'level': 2},
    {'id': 4, 'name': 'P2', 'source_value': 'P2', 'short_name': 'P2',
     'local_id': 'Local P2', 'type_source_value': 'Groupe hospitalier (GH)', 'parent_id': 1, 'level': 2},
    {'id': 5, 'name': 'P3', 'source_value': 'P3', 'short_name': 'P3',
     'local_id': 'Local P3', 'type_source_value': 'Hôpital', 'parent_id': 2, 'level': 3},
    {'id': 6, 'name': 'P4', 'source_value': 'P4', 'short_name': 'P4',
     'local_id': 'Local P4', 'type_source_value': 'Hôpital', 'parent_id': 2, 'level': 3},
    {'id': 7, 'name': 'P5', 'source_value': 'P5', 'short_name': 'P5',
     'local_id': 'Local P5', 'type_source_value': 'Hôpital', 'parent_id': 2, 'level': 3},
    {'id': 8, 'name': 'P6', 'source_value': 'P6', 'short_name': 'P6',
     'local_id': 'Local P6', 'type_source_value': 'Hôpital', 'parent_id': 3, 'level': 3},
    {'id': 9, 'name': 'P7', 'source_value': 'P7', 'short_name': 'P7',
     'local_id': 'Local P7', 'type_source_value': 'Hôpital', 'parent_id': 3, 'level': 3},
    {'id': 10, 'name': 'P8', 'source_value': 'P8', 'short_name': 'P8',
     'local_id': 'Local P8', 'type_source_value': 'Hôpital', 'parent_id': 4, 'level': 3},
    {'id': 11, 'name': 'P9', 'source_value': 'P9', 'short_name': 'P9',
     'local_id': 'Local P9', 'type_source_value': 'Hôpital', 'parent_id': 4, 'level': 3},
    {'id': 12, 'name': 'P10', 'source_value': 'P10', 'short_name': 'P10',
     'local_id': 'Local P10', 'type_source_value': 'Hôpital', 'parent_id': 4, 'level': 3},
    {'id': 13, 'name': 'P11', 'source_value': 'P11', 'short_name': 'P11',
     'local_id': 'Local P11', 'type_source_value': 'Pôle/DMU', 'parent_id': 6, 'level': 4},
    {'id': 14, 'name': 'P12', 'source_value': 'P12', 'short_name': 'P12',
     'local_id': 'Local P12', 'type_source_value': 'Pôle/DMU', 'parent_id': 6, 'level': 4},
    {'id': 15, 'name': 'P13', 'source_value': 'P13', 'short_name': 'P13',
     'local_id': 'Local P13', 'type_source_value': 'Pôle/DMU', 'parent_id': 12, 'level': 4},
    {'id': 16, 'name': 'P14', 'source_value': 'P14', 'short_name': 'P14',
     'local_id': 'Local P14', 'type_source_value': 'Pôle/DMU', 'parent_id': 12, 'level': 4}
    ]


def create_perimeters_hierarchy():
    for data in PERIMETERS_DATA:
        Perimeter.objects.create(**data)


class AccessesAppTestsBase(ViewSetTests):
    objects_url: str
    create_view: any
    update_view: any
    delete_view: any
    list_view: any
    retrieve_view: any
    model: Model
    model_objects: Manager
    model_fields: List[Field]

    def setUp(self):
        super().setUp()
        create_perimeters_hierarchy()
        self.aphp = Perimeter.objects.get(id=1)
        


from typing import List

from django.db.models import Model, Manager, Field

from accesses.models import Perimeter, Role
from accesses.services.shared import all_rights
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
           P11         P12                                                  P13          P14
"""

PERIMETERS_DATA = [
    {'id': 1, 'name': 'APHP', 'source_value': 'APHP', 'short_name': 'AP-HP', 'local_id': 'Local 00', 'type_source_value': 'AP-HP',
     'parent_id': None, 'level': 1, 'above_levels_ids': ''},
    {'id': 2, 'name': 'P0', 'source_value': 'P0', 'short_name': 'P0', 'local_id': 'Local P0', 'type_source_value': 'Groupe hospitalier (GH)',
     'parent_id': 1, 'level': 2, 'above_levels_ids': '1'},
    {'id': 3, 'name': 'P1', 'source_value': 'P1', 'short_name': 'P1', 'local_id': 'Local P1', 'type_source_value': 'Groupe hospitalier (GH)',
     'parent_id': 1, 'level': 2, 'above_levels_ids': '1'},
    {'id': 4, 'name': 'P2', 'source_value': 'P2', 'short_name': 'P2', 'local_id': 'Local P2', 'type_source_value': 'Groupe hospitalier (GH)',
     'parent_id': 1, 'level': 2, 'above_levels_ids': '1'},
    {'id': 5, 'name': 'P3', 'source_value': 'P3', 'short_name': 'P3', 'local_id': 'Local P3', 'type_source_value': 'Hôpital', 'parent_id': 2,
     'level': 3, 'above_levels_ids': '2,1'},
    {'id': 6, 'name': 'P4', 'source_value': 'P4', 'short_name': 'P4', 'local_id': 'Local P4', 'type_source_value': 'Hôpital', 'parent_id': 2,
     'level': 3, 'above_levels_ids': '2,1'},
    {'id': 7, 'name': 'P5', 'source_value': 'P5', 'short_name': 'P5', 'local_id': 'Local P5', 'type_source_value': 'Hôpital', 'parent_id': 2,
     'level': 3, 'above_levels_ids': '2,1'},
    {'id': 8, 'name': 'P6', 'source_value': 'P6', 'short_name': 'P6', 'local_id': 'Local P6', 'type_source_value': 'Hôpital', 'parent_id': 3,
     'level': 3, 'above_levels_ids': '3,1'},
    {'id': 9, 'name': 'P7', 'source_value': 'P7', 'short_name': 'P7', 'local_id': 'Local P7', 'type_source_value': 'Hôpital', 'parent_id': 3,
     'level': 3, 'above_levels_ids': '3,1'},
    {'id': 10, 'name': 'P8', 'source_value': 'P8', 'short_name': 'P8', 'local_id': 'Local P8', 'type_source_value': 'Hôpital', 'parent_id': 4,
     'level': 3, 'above_levels_ids': '4,1'},
    {'id': 11, 'name': 'P9', 'source_value': 'P9', 'short_name': 'P9', 'local_id': 'Local P9', 'type_source_value': 'Hôpital', 'parent_id': 4,
     'level': 3, 'above_levels_ids': '4,1'},
    {'id': 12, 'name': 'P10', 'source_value': 'P10', 'short_name': 'P10', 'local_id': 'Local P10', 'type_source_value': 'Hôpital', 'parent_id': 4,
     'level': 3, 'above_levels_ids': '4,1'},
    {'id': 13, 'name': 'P11', 'source_value': 'P11', 'short_name': 'P11', 'local_id': 'Local P11', 'type_source_value': 'Pôle/DMU', 'parent_id': 6,
     'level': 4, 'above_levels_ids': '6,2,1'},
    {'id': 14, 'name': 'P12', 'source_value': 'P12', 'short_name': 'P12', 'local_id': 'Local P12', 'type_source_value': 'Pôle/DMU', 'parent_id': 6,
     'level': 4, 'above_levels_ids': '6,2,1'},
    {'id': 15, 'name': 'P13', 'source_value': 'P13', 'short_name': 'P13', 'local_id': 'Local P13', 'type_source_value': 'Pôle/DMU',
     'parent_id': 12, 'level': 4, 'above_levels_ids': '12,4,1'},
    {'id': 16, 'name': 'P14', 'source_value': 'P14', 'short_name': 'P14', 'local_id': 'Local P14', 'type_source_value': 'Pôle/DMU',
     'parent_id': 12, 'level': 4, 'above_levels_ids': '12,4,1'}
    ]

ALL_FALSY_RIGHTS = {right.name: False for right in all_rights}

role_full_admin_data = {**{right.name: True for right in all_rights}, "name": "FULL ADMIN"}

role_admin_accesses_reader_data = {**ALL_FALSY_RIGHTS,
                                   "name": "ADMIN ACCESSES READER",
                                   "right_read_users": True,
                                   "right_read_admin_accesses_same_level": True,
                                   "right_read_admin_accesses_inferior_levels": True
                                   }
role_admin_accesses_manager_data = {**role_admin_accesses_reader_data,
                                    "name": "ADMIN ACCESSES MANAGER",
                                    "right_manage_users": True,
                                    "right_manage_admin_accesses_same_level": True,
                                    "right_manage_admin_accesses_inferior_levels": True,
                                    }
role_data_accesses_manager_data = {**ALL_FALSY_RIGHTS,
                                   "name": "DATA ACCESSES MANAGER",
                                   "right_manage_users": True,
                                   "right_read_users": True,
                                   "right_manage_data_accesses_same_level": True,
                                   "right_read_data_accesses_same_level": True,
                                   "right_manage_data_accesses_inferior_levels": True,
                                   "right_read_data_accesses_inferior_levels": True
                                   }
role_data_reader_nomi_pseudo_data = {**ALL_FALSY_RIGHTS,
                                     "name": "DATA NOMI/PSEUDO READER",
                                     "right_read_patient_nominative": True,
                                     "right_read_patient_pseudonymized": True,
                                     }
role_data_reader_nomi_csv_exporter_nomi_data = {**ALL_FALSY_RIGHTS,
                                                "name": "DATA NOMI READER + CSV EXPORTER",
                                                "right_read_patient_nominative": True,
                                                "right_export_csv_nominative": True
                                                }
role_csv_jupyter_exporter_pseudo_data = {**ALL_FALSY_RIGHTS,
                                         "name": "CSV + JUPYTER EXPORTER PSEUDO",
                                         "right_export_csv_pseudonymized": True,
                                         "right_export_jupyter_pseudonymized": True
                                         }
role_search_by_ipp_and_search_opposed_data = {**ALL_FALSY_RIGHTS,
                                              "name": "SEARCH BY IPP + OPPOSED PATIENTS",
                                              "right_search_patients_by_ipp": True,
                                              "right_search_opposed_patients": True
                                              }


def create_perimeters_hierarchy():
    all_perimeters = []
    for data in PERIMETERS_DATA:
        all_perimeters.append(Perimeter.objects.create(**data))
    return all_perimeters


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
        self.all_perimeters = create_perimeters_hierarchy()
        self.aphp = Perimeter.objects.get(id=1)
        self.p0 = Perimeter.objects.get(id=2)
        self.p1 = Perimeter.objects.get(id=3)
        self.p2 = Perimeter.objects.get(id=4)
        self.p3 = Perimeter.objects.get(id=5)
        self.p4 = Perimeter.objects.get(id=6)
        self.p5 = Perimeter.objects.get(id=7)
        self.p6 = Perimeter.objects.get(id=8)
        self.p7 = Perimeter.objects.get(id=9)
        self.p8 = Perimeter.objects.get(id=10)
        self.p9 = Perimeter.objects.get(id=11)
        self.p10 = Perimeter.objects.get(id=12)
        self.p11 = Perimeter.objects.get(id=13)
        self.p12 = Perimeter.objects.get(id=14)
        self.p13 = Perimeter.objects.get(id=15)
        self.p14 = Perimeter.objects.get(id=16)

        self.role_full_admin = Role.objects.create(**role_full_admin_data)
        self.role_admin_accesses_manager = Role.objects.create(**role_admin_accesses_manager_data)
        self.role_admin_accesses_reader = Role.objects.create(**role_admin_accesses_reader_data)
        self.role_data_accesses_manager = Role.objects.create(**role_data_accesses_manager_data)
        self.role_data_reader_nomi_pseudo = Role.objects.create(**role_data_reader_nomi_pseudo_data)
        self.role_data_reader_nomi_csv_exporter_nomi = Role.objects.create(**role_data_reader_nomi_csv_exporter_nomi_data)
        self.role_csv_jupyter_exporter_pseudo = Role.objects.create(**role_csv_jupyter_exporter_pseudo_data)
        self.role_search_by_ipp_and_search_opposed = Role.objects.create(**role_search_by_ipp_and_search_opposed_data)

ROOT_PERIMETER_ID = 999999

concepts_data = [{'concept_id': 1, 'concept_name': 'Care site'},
                 {'concept_id': 2, 'concept_name': 'Care Site is part of Care Site'}]

lists_data = [['id', 'size', 'source_reference_id', 'source_type', 'delete_datetime'],
              [(1, 100, f'{ROOT_PERIMETER_ID}', 'Organization', None),
               (2, 55, '0', 'Organization', None),
               (3, 17, '1', 'Organization', None),
               (4, 1, '2', 'Organization', None),
               (5, 5, '3', 'Organization', None),
               (6, 6, '4', 'Organization', None),
               (7, 12, '5', 'Organization', None),
               (8, 11, '6', 'Organization', None),
               (9, 10, '7', 'Organization', None),
               (10, 9, '8', 'Organization', None),
               (11, 8, '9', 'Organization', None),
               ]]

care_sites_data = [['care_site_id', 'care_site_name', 'care_site_short_name', 'care_site_source_value',
                    'care_site_type_source_value', 'delete_datetime'],
                   [(ROOT_PERIMETER_ID, 'APHP', 'APHP', 'APHP', 'TYPE0', None),
                    (0, 'P0', 'P0', 'P0', 'TYPE1', None),
                    (1, 'P1', 'P1', 'P1', 'TYPE1', None),
                    (2, 'P3', 'P3', 'P3', 'TYPE2', None),
                    (3, 'P4', 'P4', 'P4', 'TYPE2', None),
                    (4, 'P5', 'P5', 'P5', 'TYPE2', None),
                    (5, 'P6', 'P6', 'P6', 'TYPE2', None),
                    (6, 'P11', 'P11', 'P11', 'TYPE3', None),
                    (7, 'P12', 'P12', 'P12', 'TYPE3', None),
                    (8, 'P13', 'P13', 'P13', 'TYPE3', None),
                    (9, 'P14', 'P14', 'P14', 'TYPE3', None)]]

fact_rels_data = [['row_id', 'fact_id_1', 'fact_id_2', 'domain_concept_id_1', 'domain_concept_id_2', 'relationship_concept_id'],
                  [(1, 0, ROOT_PERIMETER_ID, 1, 1, 2),
                   (2, 1, ROOT_PERIMETER_ID, 1, 1, 2),
                   (3, 2, 0, 1, 1, 2),
                   (4, 3, 0, 1, 1, 2),
                   (5, 4, 1, 1, 1, 2),
                   (6, 5, 1, 1, 1, 2),
                   (7, 6, 2, 1, 1, 2),
                   (8, 8, 2, 1, 1, 2),
                   (9, 7, 4, 1, 1, 2),
                   (10, 9, 4, 1, 1, 2)]]

existing_perimeter_data = [
    {
        'id': 3,
        'local_id': '3',
        'cohort_id': '5',
    },
    {
        'id': 4,
        'local_id': '4',
        'cohort_id': '4',
    }
]

users_data = [
    {
        'username': '1',
        'email': 'user1@example.com',
        'firstname': 'User',
        'lastname': 'One'
    }
]

folders_data = [
    {
        'name': 'Folder 1',
        'owner_id': 1
    }
]

requests_data = [
    {
        'owner_id': 1,
        'name': 'Request 1',
        'description': 'Description for Request 1',
        'favorite': False,
        'data_type_of_query': 'PATIENT',
        'shared_by_id': None
    }
]

request_query_snapshots_data = [
    {
        'title': 'Snapshot 1',
        'owner_id': 1,
        'serialized_query': '{"sourcePopulation": {"caresiteCohortList": ["1", "2", "3"]}}',
        'translated_query': None,
        'previous_snapshot_id': None,
        'shared_by_id': None,
        'perimeters_ids': ['1', '2', '3'],
        'version': 1
    },
    {
        'title': 'Snapshot 2',
        'owner_id': 1,
        'serialized_query': '{"sourcePopulation": {"caresiteCohortList": ["4", "5", "6"]}}',
        'translated_query': None,
        'previous_snapshot_id': None,
        'shared_by_id': None,
        'perimeters_ids': ['4', '5', '6'],
        'version': 1
    },
    {
        'title': 'Snapshot 3',
        'owner_id': 1,
        'serialized_query': '{"sourcePopulation": {"caresiteCohortList": ["7", "8", "9"]}}',
        'translated_query': None,
        'previous_snapshot_id': None,
        'shared_by_id': None,
        'perimeters_ids': ['7', '8', '9'],
        'version': 1
    },
    {
        'title': 'Snapshot 4',
        'owner_id': 1,
        'serialized_query': '{"sourcePopulation": {"caresiteCohortList": ["10", "11"]}}',
        'translated_query': None,
        'previous_snapshot_id': None,
        'shared_by_id': None,
        'perimeters_ids': ['10', '11'],
        'version': 1
    }
]
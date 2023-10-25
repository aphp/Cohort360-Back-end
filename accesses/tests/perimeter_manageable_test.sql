--------- TEST

----- INSERT PROFILE
INSERT INTO "user" (firstname, lastname, provider_id, provider_username, email)
VALUES ('Nicolas', 'Puchois', 2, '7020135', 'nicolas.puchois-ext@aphp.fr');
INSERT INTO accesses_profile (id, user_id, source, is_active, firstname, lastname, email)
VALUES (5, '7020135', 'Manual', 't', 'Nicolas', 'Puchois', 'nicolas.puchois-ext@aphp.fr');


------- INSERT ROLE
INSERT INTO accesses_role (id, name, right_manage_roles, right_manage_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudonymized, invalid_reason, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users)
VALUES (-6, 'SAME_LEVEL', 'f', 'f', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f',
        'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f');

INSERT INTO accesses_role (id, name, right_manage_roles, right_manage_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudonymized, invalid_reason, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users)
VALUES (-7, 'INF_LEVEL', 'f', 'f', 'f', 'f', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f',
        'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f');


---------------- PERIMETERS

---  8312002244 APHP -> ...
---  8312019558 GH TENON -> 8312019560 HOPITAL TENON
---  8312026113 GH CHARLES FOIX -> 8312026114 HOPITAL Charles foix
---  TENON HP CHILDERN -> (8312005137, 8312005162, 8312017569, 8653815594, 8653815595, 8653815596, 8653815597, 8653815598, 8653815599, 8653815600, 8653815601, 8653815602, 8653815603, 8653815753, 8653815754, 8653815755)
--- HP CHARLES FOIX CHILDREN -> (8312024693, 8312027341, 8382309304, 8653815339, 8653815340, 8653815341, 8653815342, 8653815343, 8653815344, 8653815565, 18397444868)
---  8312019558 GH TENON -> 8312019560 HOPITAL TENON -> 8653815594 TNN DIAMENT -> 8312005058 TNN ANATOMIE PATHO
--------- CLEAR ACCESSES:
UPDATE accesses_access
SET delete_datetime = CURRENT_TIMESTAMP
WHERE profile_id = 5;


---  TEST 0: ADMIN FULL
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (1, 8312019558, 5);

--- TEST 1: SIMPLE ROLE SAME LEVEL GH TENON & HP charles foix
--- => 2 res au total
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-6, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-6, 8312026114, 5);

--- TEST 2: SIMPLE ROLE INF LEVEL GH TENON & HP charles foix
-- => 12 Results au total
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312026114, 5);

--- TEST 3: SIMPLE ROLE SAME LEVEL GH TENON & HP TENON
-- => 1 result GH TENON
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-6, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-6, 8312019560, 5);

--- TEST 4: MULTI ROLE GH TENON same level & HP TENON inf level
-- => 1 result GH TENON
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-6, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312019560, 5);

--- TEST 5: MULTI ROLE GH TENON inf level & HP TENON same level
-- => 1 result HP TENON
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-6, 8312019560, 5);

--- TEST 6: MULTI ROLE  GH TENON inf level & GH TENON same level
-- => 1 result GH TENON
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-6, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312019558, 5);

--- TEST 7: MULTI ROLE  GH TENON inf level & HP TENON inf level
-- => 1 result HP TENON
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312019560, 5);

--- TEST 8: Large distance in hierarchy ROLE GH TENON inf level &  TNN ANATOMIE PATHO inf level
-- => 1 result HP TENON
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312005058, 5);

--- TEST 9: Large distance in hierarchy ROLE HP CHARLES FROIX inf level &  TNN ANATOMIE PATHO inf level
-- => 13 result:  11 children  HP CF & 2 children TNN ANAT PATHO
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312026114, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-7, 8312005058, 5);
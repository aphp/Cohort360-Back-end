--------- TEST

----- INSERT PROFILE
INSERT INTO "user" (firstname, lastname, provider_id, provider_username, email)
VALUES ('Nicolas', 'Puchois', 2, '7020135', 'nicolas.puchois-ext@aphp.fr');
INSERT INTO accesses_profile (id, user_id, source, is_active, firstname, lastname, email)
VALUES (5, '7020135', 'Manual', 't', 'Nicolas', 'Puchois', 'nicolas.puchois-ext@aphp.fr');


------- INSERT ROLE
INSERT INTO accesses_role (id, name, right_manage_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudonymized, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudonymized, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_datalabs, right_read_datalabs)
VALUES (-10, 'READ_ALL', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 't', 'f', 't', 'f', 'f', 'f',
        'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f');

INSERT INTO accesses_role (id, name, right_manage_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudonymized, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudonymized, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_datalabs, right_read_datalabs)
VALUES (-11, 'READ_ONLY_NOMINATIVE', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 't', 'f', 'f', 'f',
        'f', 'f',
        'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f');

INSERT INTO accesses_role (id, name, right_manage_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudonymized, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudonymized, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_datalabs, right_read_datalabs)
VALUES (-12, 'READ_ONLY_PSEUDO', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 't', 'f', 'f',
        'f',
        'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f');

INSERT INTO accesses_role (id, name, right_manage_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudonymized, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudonymized, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_datalabs, right_read_datalabs)
VALUES (-13, 'NO_READ_RIGHT', 'f', 'f', 'f', 't', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f',
        'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f');

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


---  TEST 0: NO READ ROLE
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-13, 8312019558, 5);

--- TEST 1: READ ALL GH TENON & HP charles foix
--- => 2 res au total
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-10, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-10, 8312026114, 5);

--- TEST 2: ONLY READ NOMI GH TENON & HP charles foix
-- => 2 Results au total 8312019558 and 8312026113
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-11, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-11, 8312026113, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-11, 8312026114, 5);

--- TEST 3: ONLY READ PSEUDO GH TENON & HP charles foix
-- => 2 Results au total 8312019558 and 8312026113
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-12, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-12, 8312026113, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-12, 8312026114, 5);


--- TEST 4: MIX NOMI GH TENON & PSEUDO HP TENON
-- => 1 result GH TENON NOMI
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-11, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-12, 8312019560, 5);

--- TEST 5: MIX PSEUDO GH TENON & NOMI HP TENON
-- => 2 results GH TENON PSEUDO AND HP TENON NOMI
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-12, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-11, 8312019560, 5);

--- TEST 6: MIX PSEUDO GH TENON & NOMI HP TENON
-- => 2 results GH TENON PSEUDO AND GH CHARLES FOIX NOMI
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-12, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-11, 8312026113, 5);
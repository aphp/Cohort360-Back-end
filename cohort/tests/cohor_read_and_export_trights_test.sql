--------- TEST
----- FOR THIS TEST YOU NEED TO HAVE ALL PERIMETERS LOAD IN DB WITH ACCESSES.CONF_PERIMETERS.PY

----- INSERT PROFILE
INSERT INTO "user" (firstname, lastname, provider_id, provider_username, email)
VALUES ('Nicolas', 'Puchois', 2, '7020135', 'nicolas.puchois-ext@aphp.fr');
INSERT INTO accesses_profile (id, user_id, source, is_active, firstname, lastname, email)
VALUES (5, '7020135', 'Manual', 't', 'Nicolas', 'Puchois', 'nicolas.puchois-ext@aphp.fr');


------- INSERT ROLE
INSERT INTO accesses_role (id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users)
VALUES (-10, 'READ_ALL', 'f', 'f', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 't', 'f', 't', 'f', 'f', 'f',
        'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f');

INSERT INTO accesses_role (id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users)
VALUES (-11, 'READ_ONLY_NOMINATIVE', 'f', 'f', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 't', 'f', 'f', 'f',
        'f', 'f',
        'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f');

INSERT INTO accesses_role (id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users)
VALUES (-12, 'READ_ONLY_PSEUDO', 'f', 'f', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 't', 'f', 'f',
        'f',
        'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f');

INSERT INTO accesses_role (id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users)
VALUES (-21, 'EXPORT_NOMI', 'f', 'f', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f',
        't', 'f', 't', 't', 'f', 'f', 't', 'f', 'f', 'f', 'f', 'f', 'f');

INSERT INTO accesses_role (id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users)
VALUES (-22, 'EXPORT_PSEUDO', 'f', 'f', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f',
        'f', 't', 't', 't', 'f', 'f', 't', 'f', 'f', 'f', 'f', 'f', 'f');


INSERT INTO accesses_role (id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users)
VALUES (-32, 'TRANSFER_PSEUDO', 'f', 'f', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f',
        'f', 'f', 'f', 'f', 'f', 'f', 't', 'f', 'f', 't', 'f', 'f', 'f');


INSERT INTO accesses_role (id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users)
VALUES (-31, 'TRANSFER_NOMI', 'f', 'f', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f',
        'f', 'f', 'f', 'f', 'f', 'f', 't', 'f', 't', 'f', 'f', 'f', 'f');

INSERT INTO accesses_role (id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_patient_nominative, right_search_patient_with_ipp,
                           right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs,
                           right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv,
                           right_manage_review_export_csv, right_manage_review_transfer_jupyter,
                           right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter,
                           right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised,
                           right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users)
VALUES (-99, 'TRANSFER_NOMI', 'f', 'f', 'f', 'f', 't', 't', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 't', 'f', 'f', 'f',
        'f', 'f', 'f', 'f', 'f', 'f', 't', 'f', 'f', 'f', 'f', 'f', 'f');
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

--------- COHORT CREATION:
'''
u = User.objects.filter(lastname={LASTNAME}).first()
id_aphp = XXXX
f = Folder(uuid='c2d29867-3d0b-d497-9191-18a9d8ee7831',owner=u,name="FOLDER TEST")
f.save()
r = Request(owner_id=id_aphp,uuid='c2d29867-3d0b-d497-9191-18a9d8ee7830',parent_folder_id='c2d29867-3d0b-d497-9191-18a9d8ee7831',name='TEST NICO')
r.save()
rq = RequestQuerySnapshot(owner_id=id_aphp,uuid='c2d29867-3d0b-d497-9191-18a9d8ee7830',request_id='c2d29867-3d0b-d497-9191-18a9d8ee7830')
rq.save()
d = DatedMeasure(owner=u,request_query_snapshot_id='c2d29867-3d0b-d497-9191-18a9d8ee7830',uuid='c2d29867-3d0b-d497-9191-18a9d8ee7830')
d.save()
c = CohortResult(owner=u, owner_id=id_aphp , fhir_group_id={COHORT_ID} , dated_measure_id='c2d29867-3d0b-d497-9191-18a9d8ee7830',request_query_snapshot_id='c2d29867-3d0b-d497-9191-18a9d8ee7830')
c.save()
'''
---  TEST 0: NO READ ROLE
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-10, 8312002244, 5);

--- TEST 1: READ NOMI GH TENON & READ PSEUDO HP charles foix
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-11, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-11, 8312027341, 5);
--- TEST 1: READ NOMI GH TENON & READ PSEUDO HP charles foix
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-11, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-12, 8312026114, 5);


--- TEST 2: EXPORT NOMI GH TENON & EXPORT PSEUDO HP charles foix
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-21, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-22, 8312026113, 5);

--- TEST 3: TRANSFER JUP NOMI GH TENON & TRANSFER JUP PSEUDO HP charles foix
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-31, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-32, 8312026113, 5);

--- TEST SEARCH IPP:
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-99, 8312019558, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-99, 8312026113, 5);

--- TEST 4: Hopital TENON (lvl inf GH) ALL NOMI
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-11, 8312019560, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-21, 8312019560, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-31, 8312019560, 5);


--- TEST 5: Hopitam Charles Foix ALL PSEUDO
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-12, 8312026114, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-22, 8312026114, 5);
INSERT INTO accesses_access (role_id, perimeter_id, profile_id)
VALUES (-32, 8312026114, 5);
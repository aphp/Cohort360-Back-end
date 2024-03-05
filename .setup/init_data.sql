
-------------------------------------------------- User setup

INSERT INTO "user" (username, provider_id, firstname , lastname, email)
VALUES ('1234567', '1234567', '<Firstname>', '<LASTNAME>', 'firstname.lastname@cohort360.fr');

INSERT INTO accesses_profile (id, user_id, source, is_active, firstname, lastname, email)
VALUES (1, '1234567', 'Manual', 't', '<Firstname>', '<LASTNAME>', 'firstname.lastname@cohort360.fr');

-- Basic perimeters tree
INSERT INTO accesses_perimeter (id, name, source_value, type_source_value, short_name, local_id, cohort_id, parent_id)
VALUES (1, 'APHP', 'AP-HP', 'AP-HP', 'AP-HP', 'Local 00', '00', null),
       (2, 'Hopit 1', 'Hopital 01', 'Hopit 1', 'Hopital', 'Local 01', '01', 1),
       (3, 'Hopit 2', 'Hopital 02', 'Hopit 2', 'Hopital', 'Local 02', '02', 1);

-- Full admin role
INSERT INTO accesses_role (id, name, right_full_admin, right_manage_users, right_read_users,
                           right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level,
                           right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels,
                           right_manage_data_accesses_same_level, right_read_data_accesses_same_level,
                           right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels,
                           right_read_accesses_above_levels, right_read_patient_nominative, right_search_patients_by_ipp,
                           right_read_patient_pseudonymized, right_read_logs, right_export_csv_nominative, right_export_csv_pseudonymized,
                           right_manage_export_csv_accesses, right_manage_export_jupyter_accesses, right_export_jupyter_nominative,
                           right_export_jupyter_pseudonymized, right_manage_datalabs, right_read_datalabs, right_search_opposed_patients)
                     VALUES(1,'FULL_ADMIN','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t', 't','t','t','t','t','t','t','t','t');
-- Attribute admin role to admin profile
INSERT INTO accesses_access (role_id, perimeter_id, profile_id, start_datetime, end_datetime)
VALUES (1, 1, 1, now(), '2099-12-12 00:00');


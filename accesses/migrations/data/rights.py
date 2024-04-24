rights = [
    {
        "name": "right_full_admin",
        "label": "Admin Central",
        "category": "Administration",
        "is_global": True,
    },
    {
        "name": "right_read_logs",
        "label": "Consulter les logs",
        "category": "Logs",
        "is_global": True,
    },
    {
        "name": "right_manage_users",
        "label": "Gérer la liste des utilisateurs / profils",
        "category": "Utilisateurs",
        "is_global": True,
    },
    {
        "name": "right_manage_datalabs",
        "label": "Gérer les environnements de travail",
        "category": "Datalabs",
        "is_global": True,
    },
    {
        "label": "Gérer les accès permettant de réaliser des exports de données en format CSV",
        "name": "right_manage_export_csv_accesses",
        "category": "Accès Export",
        "is_global": True,
    },
    {
        "label": "Gérer les accès permettant d'exporter les cohortes vers des environnements Jupyter",
        "name": "right_manage_export_jupyter_accesses",
        "category": "Accès Export",
        "is_global": True,
    },
    {
        "label": "Demander à exporter ses cohortes de patients sous forme nominative en format CSV",
        "name": "right_export_csv_nominative",
        "category": "Exports CSV",
        "is_global": True,
    },
    {
        "label": "Demander à exporter ses cohortes de patients sous forme pseudonymisée en format CSV",
        "name": "right_export_csv_pseudonymized",
        "category": "Exports CSV",
        "is_global": True,
    },
    {
        "label": "Exporter ses cohortes de patients sous forme nominative vers un environnement Jupyter",
        "name": "right_export_jupyter_nominative",
        "category": "Exports Jupyter",
        "is_global": True,
    },
    {
        "label": "Exporter ses cohortes de patients sous forme pseudonymisée vers un environnement Jupyter",
        "name": "right_export_jupyter_pseudonymized",
        "category": "Exports Jupyter",
        "is_global": True,
    },
    {
        "label": "Chercher les patients par IPP",
        "name": "right_search_patients_by_ipp",
        "category": "Recherche de Patients",
        "is_global": True,
    },
    {
        "label": "Chercher les patients opposés à l'utilisation de leurs données pour la recherche",
        "name": "right_search_opposed_patients",
        "category": "Recherche de Patients",
        "is_global": True,
    },
    {
        "label": "Lecture de données patients nominatives",
        "name": "right_read_patient_nominative",
        "impact_inferior_levels": True,
        "category": "Lecture de Données Patients",
        "is_global": False,
    },
    {
        "label": "Lecture de données patients pseudonymisées",
        "name": "right_read_patient_pseudonymized",
        "impact_inferior_levels": True,
        "category": "Lecture de Données Patients",
        "is_global": False,
    },
    {
        "label": "Gérer les accès administrateurs d'un périmètre exclusivement",
        "name": "right_manage_admin_accesses_same_level",
        "allow_edit_accesses_on_same_level": True,
        "category": "Gestion des Accès Admin",
        "is_global": False,
    },
    {
        "label": "Gérer les accès administrateurs des sous-périmètres exclusivement",
        "name": "right_manage_admin_accesses_inferior_levels",
        "allow_edit_accesses_on_inf_levels": True,
        "impact_inferior_levels": True,
        "category": "Gestion des Accès Admin",
        "is_global": False,
    },
    {
        "label": "Gérer les accès aux données patients d'un périmètre exclusivement",
        "name": "right_manage_data_accesses_same_level",
        "allow_edit_accesses_on_same_level": True,
        "category": "Gestion des Accès Données",
        "is_global": False,
    },
    {
        "label": "Gérer les accès aux données patients des sous-périmètres exclusivement",
        "name": "right_manage_data_accesses_inferior_levels",
        "allow_edit_accesses_on_inf_levels": True,
        "impact_inferior_levels": True,
        "category": "Gestion des Accès Données",
        "is_global": False,
    },
    {
        "label": "Consulter les accès en provenance des périmètres parents d'un périmètre P",
        "name": "right_read_accesses_above_levels",
        "category": "Divers",
        "is_global": True,
    }
]

dependent_rights = [
    {
        "name": "right_read_users",
        "label": "Consulter la liste des utilisateurs / profils",
        "category": "Utilisateurs",
        "is_global": True,
        "depends_on": "right_manage_users"
    },
    {
        "name": "right_read_datalabs",
        "label": "Consulter la liste des environnements de travail",
        "category": "Datalabs",
        "is_global": True,
        "depends_on": "right_manage_datalabs"
    },
    {
        "name": "right_read_admin_accesses_same_level",
        "label": "Consulter la liste des accès administrateur d'un périmètre exclusivement",
        "allow_read_accesses_on_same_level": True,
        "category": "Gestion des Accès Admin",
        "is_global": False,
        "depends_on": "right_manage_admin_accesses_same_level"
    },
    {
        "name": "right_read_admin_accesses_inferior_levels",
        "label": "Consulter la liste des accès administrateur des sous-périmètres exclusivement",
        "allow_read_accesses_on_inf_levels": True,
        "impact_inferior_levels": True,
        "category": "Gestion des Accès Admin",
        "is_global": False,
        "depends_on": "right_manage_admin_accesses_inferior_levels"
    },
    {
        "name": "right_read_data_accesses_same_level",
        "label": "Consulter la liste des accès aux données patients d'un périmètre exclusivement",
        "allow_read_accesses_on_same_level": True,
        "category": "Gestion des Accès Données",
        "is_global": False,
        "depends_on": "right_manage_data_accesses_same_level"
    },
    {
        "name": "right_read_data_accesses_inferior_levels",
        "label": "Consulter la liste des accès aux données patients des sous-périmètres exclusivement",
        "allow_read_accesses_on_inf_levels": True,
        "impact_inferior_levels": True,
        "category": "Gestion des Accès Données",
        "is_global": False,
        "depends_on": "right_manage_data_accesses_inferior_levels"
    }
]

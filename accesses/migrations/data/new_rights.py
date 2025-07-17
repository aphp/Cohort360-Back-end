rights = [
    {
        "name": "right_full_admin",
        "label": "Administrateur",
        "category": "Administration",
        "is_global": True,
    },
    {
        "name": "right_manage_users",
        "label": "Gérer la liste des utilisateurs",
        "category": "Utilisateurs",
        "is_global": True,
    },
    {
        "label": "Gérer les accès aux données patient d'un périmètre exclusivement",
        "name": "right_manage_data_accesses_same_level",
        "allow_edit_accesses_on_same_level": True,
        "category": "Gestion des Accès Données",
        "is_global": False,
    },
    {
        "label": "Gérer les accès aux données patient des sous-périmètres exclusivement",
        "name": "right_manage_data_accesses_inferior_levels",
        "allow_edit_accesses_on_inf_levels": True,
        "impact_inferior_levels": True,
        "category": "Gestion des Accès Données",
        "is_global": False,
    },
    {
        "label": "Gérer les accès administrateurs d'un périmètre exclusivement",
        "name": "right_manage_admin_accesses_same_level",
        "allow_edit_accesses_on_same_level": True,
        "category": "Gestion des Accès Administrateurs",
        "is_global": False,
    },
    {
        "label": "Gérer les accès administrateurs des sous-périmètres exclusivement",
        "name": "right_manage_admin_accesses_inferior_levels",
        "allow_edit_accesses_on_inf_levels": True,
        "impact_inferior_levels": True,
        "category": "Gestion des Accès Administrateurs",
        "is_global": False,
    },
    {
        "label": "Lecture de données patient nominatives",
        "name": "right_read_patient_nominative",
        "impact_inferior_levels": True,
        "category": "Lecture de Données Patient",
        "is_global": False,
    },
    {
        "label": "Lecture de données patient pseudonymisées",
        "name": "right_read_patient_pseudonymized",
        "impact_inferior_levels": True,
        "category": "Lecture de Données Patient",
        "is_global": False,
    },
    {
        "label": "Chercher les patients par IPP",
        "name": "right_search_patients_by_ipp",
        "category": "Recherche de Patients",
        "is_global": True,
    },
    {
        "label": "Chercher les patients sans limite de périmètre (PP)",
        "name": "right_search_patients_unlimited",
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
        "label": "Exporter ses cohortes de patients sous forme nominative en format CSV-Excel",
        "name": "right_export_csv_xlsx_nominative",
        "category": "Exports CSV-Excel",
        "is_global": True,
    },
    {
        "label": "Consulter les accès en provenance des périmètres parents",
        "name": "right_read_accesses_above_levels",
        "category": "Divers",
        "is_global": True,
    },
    {
        "name": "right_manage_datalabs",
        "label": "Gérer la liste des datalabs",
        "category": "Datalabs",
        "is_global": True,
    }
]

dependent_rights = [
    {
        "name": "right_read_datalabs",
        "label": "Consulter la liste des datalabs",
        "category": "Datalabs",
        "is_global": True,
        "depends_on": "right_manage_datalabs"
    },
]

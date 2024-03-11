right_categories = [
    {
        "name": "Administration",
        "is_global": True,
        "rights": [{"label": "Admin Central", "name": "right_full_admin"}]
    },
    {
        "name": "Logs",
        "is_global": True,
        "rights": [{"label": "Consulter les logs", "name": "right_read_logs"}]
    },
    {
        "name": "Utilisateurs",
        "is_global": True,
        "rights": [
            {
                "label": "Gérer la liste des utilisateurs / profils",
                "name": "right_manage_users"
            }
        ]
    },
    {
        "name": "Datalabs",
        "is_global": True,
        "rights": [
            {
                "label": "Gérer les environnements de travail",
                "name": "right_manage_datalabs"
            }
        ]
    },
    {
        "name": "Accès Exports",
        "is_global": True,
        "rights": [
            {
                "label": "Gérer les accès permettant de réaliser des exports de données en format CSV",
                "name": "right_manage_export_csv_accesses"
            },
            {
                "label": "Gérer les accès permettant d'exporter les cohortes vers des environnements Jupyter",
                "name": "right_manage_export_jupyter_accesses"
            }
        ]
    },
    {
        "name": "Exports CSV",
        "is_global": True,
        "rights": [
            {
                "label": "Demander à exporter ses cohortes de patients sous forme nominative en format CSV",
                "name": "right_export_csv_nominative"
            },
            {
                "label": "Demander à exporter ses cohortes de patients sous forme pseudonymisée en format CSV",
                "name": "right_export_csv_pseudonymized"
            }
        ]
    },
    {
        "name": "Exports Jupyter",
        "is_global": True,
        "rights": [
            {
                "label": "Exporter ses cohortes de patients sous forme nominative vers un environnement Jupyter",
                "name": "right_export_jupyter_nominative"
            },
            {
                "label": "Exporter ses cohortes de patients sous forme pseudonymisée vers un environnement Jupyter",
                "name": "right_export_jupyter_pseudonymized"
            }
        ]
    },
    {
        "name": "Recherche de Patients",
        "is_global": True,
        "rights": [
            {
                "label": "Chercher les patients par IPP",
                "name": "right_search_patients_by_ipp"
            },
            {
                "label": "Chercher les patients opposés à l'utilisation de leurs données pour la recherche",
                "name": "right_search_opposed_patients"
            }
        ]
    },
    {
        "name": "Lecture de Données Patients",
        "is_global": False,
        "rights": [
            {
                "label": "Lecture de données patients nominatives",
                "name": "right_read_patient_nominative",
                "impact_inferior_levels": True
            },
            {
                "label": "Lecture de données patients pseudonymisées",
                "name": "right_read_patient_pseudonymized",
                "impact_inferior_levels": True
            }
        ]
    },
    {
        "name": "Gestion des Accès Admin",
        "is_global": False,
        "rights": [
            {
                "label": "Gérer les accès administrateurs d'un périmètre exclusivement",
                "name": "right_manage_admin_accesses_same_level",
                "allow_edit_accesses_on_same_level": True
            },
            {
                "label": "Gérer les accès administrateurs des sous-périmètres exclusivement",
                "name": "right_manage_admin_accesses_inferior_levels",
                "allow_edit_accesses_on_inf_levels": True,
                "impact_inferior_levels": True
            }
        ]
    },
    {
        "name": "Gestion des Accès Données",
        "is_global": False,
        "rights": [
            {
                "label": "Gérer les accès aux données patients d'un périmètre exclusivement",
                "name": "right_manage_data_accesses_same_level",
                "allow_edit_accesses_on_same_level": True
            },
            {
                "label": "Gérer les accès aux données patients des sous-périmètres exclusivement",
                "name": "right_manage_data_accesses_inferior_levels",
                "allow_edit_accesses_on_inf_levels": True,
                "impact_inferior_levels": True
            }
        ]
    },
    {
        "name": "Divers",
        "is_global": True,
        "rights": [
            {
                "label": "Consulter les accès en provenance des périmètres parents d'un périmètre P",
                "name": "right_read_accesses_above_levels"
            }
        ]
    }
]

dependent_rights = [
    {
        "label": "Consulter la liste des utilisateurs / profils",
        "name": "right_read_users",
        "depends_on": "right_manage_users"
    },
    {
        "label": "Consulter la liste des environnements de travail",
        "name": "right_read_datalabs",
        "depends_on": "right_manage_datalabs"
    },
    {
        "label": "Consulter la liste des accès administrateur d'un périmètre exclusivement",
        "name": "right_read_admin_accesses_same_level",
        "allow_read_accesses_on_same_level": True,
        "depends_on": "right_manage_admin_accesses_same_level"
    },
    {
        "label": "Consulter la liste des accès administrateur des sous-périmètres exclusivement",
        "name": "right_read_admin_accesses_inferior_levels",
        "allow_read_accesses_on_inf_levels": True,
        "impact_inferior_levels": True,
        "depends_on": "right_manage_admin_accesses_inferior_levels"
    },
    {
        "label": "Consulter la liste des accès aux données patients d'un périmètre exclusivement",
        "name": "right_read_data_accesses_same_level",
        "allow_read_accesses_on_same_level": True,
        "depends_on": "right_manage_data_accesses_same_level"
    },
    {
        "label": "Consulter la liste des accès aux données patients des sous-périmètres exclusivement",
        "name": "right_read_data_accesses_inferior_levels",
        "allow_read_accesses_on_inf_levels": True,
        "impact_inferior_levels": True,
        "depends_on": "right_manage_data_accesses_inferior_levels"
    }

]

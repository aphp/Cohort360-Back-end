rights = [
    {
        "name": "Administration",
        "is_global": True,
        "rights": [{"label": "Admin Central", "key_name": "right_full_admin"}]
    },
    {
        "name": "Logs",
        "is_global": True,
        "rights": [{"label": "Consulter les logs", "key_name": "right_read_logs"}]
    },
    {
        "name": "Utilisateurs",
        "is_global": True,
        "rights": [
            {
                "label": "Gérer la liste des utilisateurs / profils",
                "key_name": "right_manage_users"
            },
            {
                "label": "Consulter la liste des utilisateurs / profils",
                "key_name": "right_read_users"
            }
        ]
    },
    {
        "name": "Datalabs",
        "is_global": True,
        "rights": [
            {
                "label": "Gérer les environnements de travail",
                "key_name": "right_manage_datalabs"
            },
            {
                "label": "Consulter la liste des environnements de travail",
                "key_name": "right_read_datalabs"
            }
        ]
    },
    {
        "name": "Accès Exports",
        "is_global": True,
        "rights": [
            {
                "label": "Gérer les accès permettant de réaliser des exports de données en format CSV",
                "key_name": "right_manage_export_csv_accesses"
            },
            {
                "label": "Gérer les accès permettant d'exporter les cohortes vers des environnements Jupyter",
                "key_name": "right_manage_export_jupyter_accesses"
            }
        ]
    },
    {
        "name": "Exports CSV",
        "is_global": True,
        "rights": [
            {
                "label": "Demander à exporter ses cohortes de patients sous forme nominative en format CSV",
                "key_name": "right_export_csv_nominative"
            },
            {
                "label": "Demander à exporter ses cohortes de patients sous forme pseudonymisée en format CSV",
                "key_name": "right_export_csv_pseudonymized"
            }
        ]
    },
    {
        "name": "Exports Jupyter",
        "is_global": True,
        "rights": [
            {
                "label": "Exporter ses cohortes de patients sous forme nominative vers un environnement Jupyter",
                "key_name": "right_export_jupyter_nominative"
            },
            {
                "label": "Exporter ses cohortes de patients sous forme pseudonymisée vers un environnement Jupyter",
                "key_name": "right_export_jupyter_pseudonymized"
            }
        ]
    },
    {
        "name": "Recherche de Patients",
        "is_global": True,
        "rights": [
            {
                "label": "Chercher les patients par IPP",
                "key_name": "right_search_patients_by_ipp"
            },
            {
                "label": "Chercher les patients opposés à l'utilisation de leurs données pour la recherche",
                "key_name": "right_search_opposed_patients"
            }
        ]
    },
    {
        "name": "Lecture de Données Patients",
        "is_global": False,
        "rights": [
            {
                "label": "Lecture de données patients nominatives",
                "key_name": "right_read_patient_nominative"
            },
            {
                "label": "Lecture de données patients pseudonymisées",
                "key_name": "right_read_patient_pseudonymized"
            }
        ]
    },
    {
        "name": "Gestion des Accès Admin",
        "is_global": False,
        "rights": [
            {
                "label": "Gérer les accès administrateurs d'un périmètre exclusivement",
                "key_name": "right_manage_admin_accesses_same_level"
            },
            {
                "label": "Consulter la liste des accès administrateur d'un périmètre exclusivement",
                "key_name": "right_read_admin_accesses_same_level"
            },
            {
                "label": "Gérer les accès administrateurs des sous-périmètres exclusivement",
                "key_name": "right_manage_admin_accesses_inferior_levels"
            },
            {
                "label": "Consulter la liste des accès administrateur des sous-périmètres exclusivement",
                "key_name": "right_read_admin_accesses_inferior_levels"
            }
        ]
    },
    {
        "name": "Gestion des Accès Données",
        "is_global": False,
        "rights": [
            {
                "label": "Gérer les accès aux données patients d'un périmètre exclusivement",
                "key_name": "right_manage_data_accesses_same_level"
            },
            {
                "label": "Consulter la liste des accès aux données patients d'un périmètre exclusivement",
                "key_name": "right_read_data_accesses_same_level"
            },
            {
                "label": "Gérer les accès aux données patients des sous-périmètres exclusivement",
                "key_name": "right_manage_data_accesses_inferior_levels"
            },
            {
                "label": "Consulter la liste des accès aux données patients des sous-périmètres exclusivement",
                "key_name": "right_read_data_accesses_inferior_levels"
            }
        ]
    },
    {
        "name": "Divers",
        "is_global": True,
        "rights": [
            {
                "label": "Consulter les accès en provenance des périmètres parents d'un périmètre P",
                "key_name": "right_read_accesses_above_levels"
            }
        ]
    }
]

rightsDependencies = [{"dependency": "right_manage_users", "dependant": "right_read_users"},
                      {"dependency": "right_manage_datalabs", "dependant": "right_read_datalabs"},
                      {"dependency": "right_manage_admin_accesses_same_level", "dependant": "right_read_admin_accesses_same_level"},
                      {"dependency": "right_manage_admin_accesses_inferior_levels", "dependant": "right_read_admin_accesses_inferior_levels"},
                      {"dependency": "right_manage_data_accesses_same_level", "dependant": "right_read_data_accesses_same_level"},
                      {"dependency": "right_manage_data_accesses_inferior_levels", "dependant": "right_read_data_accesses_inferior_levels"}
                      ]

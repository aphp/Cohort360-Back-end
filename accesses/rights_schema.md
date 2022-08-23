```mermaid
classDiagram
class RolesEditors {
  right_edit_roles
}
class AdminManager {
  right_manage_admin_accesses_same_level
  right_read_admin_accesses_same_level
  right_manage_admin_accesses_inferior_levels
  right_read_admin_accesses_inferior_levels
}
class DataReadersAdmin {
  right_manage_data_accesses_same_level
  right_read_data_accesses_same_level
  right_manage_data_accesses_inferior_levels
  right_read_data_accesses_inferior_levels
}
class DataReader {
  right_read_patient_nominative
  right_search_patient_with_ipp
  right_read_patient_pseudo_anonymised
}
class CsvExportersAdmin {
  right_manage_export_csv
}
class JupyterExportersAdmin {
  right_manage_transfer_jupyter
}
class CsvExporters {
  right_export_csv_nominative
  right_export_csv_pseudo_anonymised
}
class JupyterExporters {
  right_transfer_jupyter_nominative
  right_transfer_jupyter_pseudo_anonymised
}
class CsvExportReviewersAdmin {
  right_manage_review_export_csv
}
class JupyterExportReviewersAdmin {
  right_manage_review_transfer_jupyter
}
class CsvExportReviewers {
  right_review_export_csv
}
class JupyterExportReviewers {
  right_review_transfer_jupyter
}
class WorkspacesManager {
  right_read_env_unix_users
  right_manage_env_unix_users
  right_manage_env_user_links
}
class UsersAdmin {
  right_add_users
  right_edit_users
  right_read_logs
}
RolesEditors --> AdminManager
RolesEditors --> UsersAdmin
AdminManager --> DataReadersAdmin
DataReadersAdmin --> DataReader

RolesEditors --> CsvExportersAdmin
RolesEditors --> JupyterExportersAdmin
CsvExportersAdmin --> CsvExporters
JupyterExportersAdmin --> JupyterExporters

RolesEditors --> CsvExportReviewersAdmin : Can manage accesses that include * - Can read accesses that at least include * (and optionally following *)
RolesEditors --> JupyterExportReviewersAdmin
CsvExportReviewersAdmin --> CsvExportReviewers
JupyterExportReviewersAdmin --> JupyterExportReviewers

RolesEditors --> WorkspacesManager

class AnyManagerAdmin {
  RolesEditors
  AdminManager
}
AnyManagerAdmin --> UsersReaders
UsersReaders : right_read_users
```

```mermaid
  graph TD
      A[RolesEditors]
      B[AdminManager]
      C(DataReadersAdmin)
      D(DataReader)

      I(ExportersAdmin)
      J(Exporters)

      M(ExportReviewersAdmin)
      N(ExportReviewers)

      U(WorkspacesManager)
      Y(UsersAdmin)

      A-->Y
      subgraph "Base"
      Y
      end

      A-->B
      subgraph "Patient data"
      B-->C
      C-->D      
      end

      A-- Can manage accesses that include * - Can read accesses that at least include * - And optionally following * -->I
      A--> M
      subgraph "Exports"
      M-->N
      I-->J
      end

      A-->U
      subgraph "Workspaces"
      U
      end

      
      Z2(UsersReaders)
      A2[RolesEditors]-->Z2
      B2[AdminManager]-->Z2
```

Comment lire ce schéma :

#### Manage

Imaginons un *Role* qui possède:
- *right_export_csv_nominative*  (**Exporters**)
- *right_manage_env_unix_users* (**WorkspacesManager**)
- *right_read_data_accesses_same_level* (**DataReadersAdmin**)

Et bien pour pouvoir attribuer ce *Role* a quelqu'un, ou modifier un *Access* qui possède ce *Role*, il faut que moi-même j'ai un Role avec :
- *right_manage_export_csv* (**ExportersAdmin**)
- *right_edit_roles* (**RolesEditors**)
- *right_manage_admin_accesses_* (**AdminManager**)

Et en effet, *right_edit_roles* **ne suffit pas** pour créer un accès avec *right_read_data_accesses_same_level* (**DataReadersAdmin**)

#### Read

En revanche, côté lecture, lorsque je fais `GET /accesses/`, s'afficheront les _Access_ avec _Role_ qui :
- possède **au moins** un _right_ de niveau directement en-dessous de mon *Role* dans le graphe
- possède **éventuellement** des _right_ de niveau encore en-dessous
- ne possède **aucun** _right_ de de mon type de _Role_ ou de _Role_ de niveau supérieur

Par exemple, si je possède _right_read_admin_accesses_ (**AdminManager**):
- apparaîtront les _Access_ avec un _Role_ contenant uniquement _right_manage_data_accesses_same_level_ (**DataReadersAdmin**) et _right_read_users_ (**UsersReaders**)
- ils apparaîtront encore si je rajoute, à ce _Role_, _right_read_patient_nominative_ (**DataReaders**) 
- n'apparaîtront plus si je rajoute, à ce _Role_, _right_read_admin_accesses_ (**DataReaders**), _right_export_csv_nominative_ (**Exporters**) ou même pire _right_edit_roles_ (**RolesEditors**)

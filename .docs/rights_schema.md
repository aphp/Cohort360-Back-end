```mermaid
  graph TD
      A(FullAdmin)
      
      B(ManageDataReadingAdministration)
      C(DataReadingAdministration)
      D(DataReading)

      B(ManageDataReadingAdministration)
      C(DataReadingAdministration)
      F(CsvExcelExports)

      B(ManageDataReadingAdministration)
      C(DataReadingAdministration)
      H(JupyterExports)

      I(Datalabs)
      J(Users)
      K(Logs)
      L(Misc)
      
      A-->E
      A-->G
      A-->I
      A-->J
      A-->K
      A-->L
      subgraph "Global Rights"
      G-->H
      E-->F
      I
      J
      K
      L
      end
      
      A-->B
      subgraph "Hierarchy Dependent Rights"
      B-->C
      C-->D      
      end      
```

```mermaid
classDiagram
class FullAdmin {
  right_full_admin
}
class ManageDataReadingAdministration {
  right_manage_admin_accesses_same_level
  right_manage_admin_accesses_inferior_levels
}
class DataReadingAdministration {
  right_manage_data_accesses_same_level
  right_manage_data_accesses_inferior_levels
}
class DataReading {
  right_read_patient_nominative
  right_read_patient_pseudonymized
  right_search_patients_by_ipp
  right_search_opposed_patients
}
class CsvExcelExports {
  right_export_csv_xlsx_nominative
}
class JupyterExports {
  right_export_jupyter_nominative
  right_export_jupyter_pseudonymized
}
class Datalabs {
  right_manage_datalabs
  right_read_datalabs
}
class Users {
  right_manage_users
}
class Misc {
  right_search_patients_by_ipp
  right_search_opposed_patients
  right_read_accesses_above_levels
}
FullAdmin --> ManageDataReadingAdministration
ManageDataReadingAdministration --> DataReadingAdministration : Administration accesses/rights
DataReadingAdministration --> DataReading : Data accesses/rights
ManageDataReadingAdministration --> CsvExcelExports
DataReadingAdministration --> CsvExcelExports
ManageDataReadingAdministration --> JupyterExports
DataReadingAdministration --> JupyterExports
FullAdmin --> Datalabs
FullAdmin --> Users
FullAdmin --> Misc
```
## 
## ℹ️ Any _access management_ right implicitly allows _reading_ as well

#### Full Admin Role:
this is a **Super User**role. It allows managing/reading everything, including managing all access.  
This role has the following right enabled:  
- *right_full_admin*
Only **one** Full Admin role is expected to be configured.

#### Data Reading Role:
It allows reading patient data and search by IPP and lookup opposing patients.  
It is any role having at least one of the following rights activated:  
- *right_read_patient_nominative*
- *right_read_patient_pseudonymized*
- *right_search_patients_by_ipp*
- *right_search_opposed_patients*

#### Data Reading Administration Role:
It allows to manage (hence read) accesses associated with Data Reading Roles.  
This is any role with at least one of the following rights enabled:  
- *right_manage_data_accesses_same_level*
- *right_manage_data_accesses_inferior_levels*

#### Manage (Data Reading Administration) Role:
It allows to manage (hence read) accesses associated with Data Reading Administration Roles.  
This is any role with at least one of the following rights enabled:  
- *right_manage_admin_accesses_same_level*
- *right_manage_admin_accesses_inferior_levels*

#### CSV/Excel Exports Role:
It allows to export data in CSV and XLSX formats.  
This is any role with at least one of the following permissions enabled:  
- *right_export_csv_xlsx_nominative*

#### Jupyter Exports Role:
It allows to export data in Hive formats to a Jupyter datalab or workspace.  
This is any role with at least one of the following permissions enabled:  
- *right_export_jupyter_nominative*
- *right_export_jupyter_pseudonymized*

#### User Role:
It allows you to manage/read the user list.  
It is any role with at least one of the following rights enabled:  
- *right_manage_users*

#### Datalabs Role:
It allows you to manage/read the list of Datalabs.  
It is any role with at least one of the following permissions enabled:  
- *right_manage_datalabs*
- *right_read_datalabs*

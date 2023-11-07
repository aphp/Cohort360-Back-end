```mermaid
classDiagram
class FullAdmin {
  right_full_admin
}
class ManageDataReadingAdministration {
  right_manage_admin_accesses_same_level
  right_read_admin_accesses_same_level
  right_manage_admin_accesses_inferior_levels
  right_read_admin_accesses_inferior_levels
}
class DataReadingAdministration {
  right_manage_data_accesses_same_level
  right_read_data_accesses_same_level
  right_manage_data_accesses_inferior_levels
  right_read_data_accesses_inferior_levels
}
class DataReading {
  right_read_patient_nominative
  right_read_patient_pseudonymized
  right_search_patients_by_ipp
  right_read_research_opposed_patient_data
}
class CSVExportsAdministration {
  right_manage_export_csv_accesses
}
class JupyterExportsAdministration {
  right_manage_export_jupyter_accesses
}
class CSVExports {
  right_export_csv_nominative
  right_export_csv_pseudonymized
}
class JupyterExports {
  right_export_jupyter_nominative
  right_export_jupyter_pseudonymized
}
class Logs {
  right_read_logs
}
class Roles {
  right_manage_roles
  right_read_roles
}
class Users {
  right_manage_users
  right_read_logs
}
class Datalabs {
  right_manage_datalabs
  right_read_datalabs
}

FullAdmin --> ManageDataReadingAdministration
ManageDataReadingAdministration --> DataReadingAdministration : Administration accesses/rights
DataReadingAdministration --> DataReading : Data accesses/rights
FullAdmin --> CSVExportsAdministration
FullAdmin --> JupyterExportsAdministration
FullAdmin --> Logs
FullAdmin --> Roles
FullAdmin --> Users
FullAdmin --> Datalabs
CSVExportsAdministration-->CSVExports
JupyterExportsAdministration-->JupyterExports
Logs
Roles
Users
Datalabs
```

```mermaid
  graph TD
      A[RolesEditors]
      B[ManageDataReadingAdministration]
      C(DataReadingAdministration)
      D(DataReading)

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
      B2[ManageDataReadingAdministration]-->Z2
```

Comment lire ce schéma :

#### Manage

Imaginons un *Role* qui possède:
- *right_export_csv_nominative*  (**Exporters**)
- *right_manage_datalabs* (**WorkspacesManager**)
- *right_read_data_accesses_same_level* (**DataReadingAdministration**)

Et bien pour pouvoir attribuer ce *Role* a quelqu'un, ou modifier un *Access* qui possède ce *Role*, il faut que moi-même j'ai un Role avec :
- *right_manage_export_csv* (**ExportersAdmin**)
- *right_manage_roles* (**RolesEditors**)
- *right_manage_admin_accesses_* (**ManageDataReadingAdministration**)

Et en effet, *right_manage_roles* **ne suffit pas** pour créer un accès avec *right_read_data_accesses_same_level* (**DataReadingAdministration**)

#### Read

En revanche, côté lecture, lorsque je fais `GET /accesses/`, s'afficheront les _Access_ avec _Role_ qui :
- possède **au moins** un _right_ de niveau directement en-dessous de mon *Role* dans le graphe
- possède **éventuellement** des _right_ de niveau encore en-dessous
- ne possède **aucun** _right_ de de mon type de _Role_ ou de _Role_ de niveau supérieur

Par exemple, si je possède _right_read_admin_accesses_ (**ManageDataReadingAdministration**):
- apparaîtront les _Access_ avec un _Role_ contenant uniquement _right_manage_data_accesses_same_level_ (**DataReadingAdministration**) et _right_read_users_ (**UsersReaders**)
- ils apparaîtront encore si je rajoute, à ce _Role_, _right_read_patient_nominative_ (**DataReaders**) 
- n'apparaîtront plus si je rajoute, à ce _Role_, _right_read_admin_accesses_ (**DataReaders**), _right_export_csv_nominative_ (**Exporters**) ou même pire _right_manage_roles_ (**RolesEditors**)


### Exemples

Considérons un schéma simplifié des droits :

```mermaid
classDiagram
class Main {
  right_manage
}
class ChildA {
  right_manageA
}
class ChildAA {
  rightA
}
class ChildB {
  right_manageB
}
class ChildBA {
  rightB
}
Main --> ChildA
Main --> ChildB
ChildA --> ChildAA
ChildB --> ChildBA
```

Pour simplifier encore, nous considérerons 

```mermaid
flowchart TD
Main --> ChildA
Main --> ChildB
ChildA --> ChildAA
ChildB --> ChildBA
style AdminHas stroke:#088,stroke-width:4px
style CanBeRead stroke:#080,stroke-width:4px
style CantBeRead stroke:#800,stroke-width:4px
```

Attention, on considère :
- qu'avoir ChildA signifie qu'on a right_read_accesses dans le cas de la lecture, et right_edit_accesses dans l'autre cas.
- uniquement les droits, et non les Périmètres (dans le cas de right_read_accesses_on_inferior_levels)

#### Lecture

##### Cas 1

Si admin possède :


```mermaid
flowchart TD
subgraph Peut lire
    subgraph admin
    direction TB
    Main --> ChildA
    Main --> ChildB
    ChildA --> ChildAA
    ChildB --> ChildBA
    style Main stroke:#088,stroke-width:4px
    end
    subgraph user1
    direction TB
    _Main --> _ChildA
    _Main --> _ChildB
    _ChildA --> _ChildAA
    _ChildB --> _ChildBA
    style _ChildB stroke:#080,stroke-width:4px
    style _ChildA stroke:#080,stroke-width:4px
    style _ChildBA stroke:#080,stroke-width:4px
    style _ChildAA stroke:#080,stroke-width:4px
    end
    subgraph user2*
    direction TB
    __Main --> __ChildA
    __Main --> __ChildB
    __ChildA --> __ChildAA
    __ChildB --> __ChildBA
    style __Main stroke:#080,stroke-width:4px
    style __ChildB stroke:#080,stroke-width:4px
    style __ChildA stroke:#080,stroke-width:4px
    style __ChildBA stroke:#080,stroke-width:4px
    style __ChildAA stroke:#080,stroke-width:4px
    end
end
```

*parce que Main n'a pas de parent, il doit pouvoir se lire lui même.

Mais ne pourra pas lire le suivant :

```mermaid
flowchart TD
subgraph Ne peut pas lire
    subgraph admin
    direction TB
    Main --> ChildA
    Main --> ChildB
    ChildA --> ChildAA
    ChildB --> ChildBA
    style Main stroke:#088,stroke-width:4px
    end
    subgraph user1
    direction TB
    _Main --> _ChildA
    _Main --> _ChildB
    _ChildA --> _ChildAA
    _ChildB --> _ChildBA
    style _ChildA stroke:#080,stroke-width:4px
    style _ChildAA stroke:#080,stroke-width:4px
    style _ChildBA stroke:#800,stroke-width:4px
    end
end
```

Car il manque dans ChildB pour lire les droits enfants.

##### Cas 2

Si admin possède ceci :

```mermaid
flowchart TD
subgraph Peut lire
    subgraph admin
    direction TB
    Main --> ChildA
    Main --> ChildB
    ChildA --> ChildAA
    ChildB --> ChildBA
    style ChildA stroke:#088,stroke-width:4px
    style ChildB stroke:#088,stroke-width:4px
    end
    subgraph user
    direction TB
    _Main --> _ChildA
    _Main --> _ChildB
    _ChildA --> _ChildAA
    _ChildB --> _ChildBA
    style _ChildBA stroke:#080,stroke-width:4px
    style _ChildAA stroke:#080,stroke-width:4px
    end
end
```

Mais :

```mermaid
flowchart TD
subgraph Ne peut pas lire
    subgraph admin
    direction TB
    Main --> ChildA
    Main --> ChildB
    ChildA --> ChildAA
    ChildB --> ChildBA
    style ChildA stroke:#088,stroke-width:4px
    style ChildB stroke:#088,stroke-width:4px
    end
    subgraph user
    direction TB
    _Main --> _ChildA
    _Main --> _ChildB
    _ChildA --> _ChildAA
    _ChildB --> _ChildBA
    style _ChildB stroke:#800,stroke-width:4px
    style _ChildBA stroke:#080,stroke-width:4px
    style _ChildAA stroke:#080,stroke-width:4px
    end
end
```

##### Cas 3

Et si admin n'a que :

```mermaid
flowchart TD
subgraph _
    subgraph admin
    direction TB
    Main --> ChildA
    Main --> ChildB
    ChildA --> ChildAA
    ChildB --> ChildBA
    style ChildA stroke:#088,stroke-width:4px
    end
    subgraph peut_lire
    direction TB
    _Main --> _ChildA
    _Main --> _ChildB
    _ChildA --> _ChildAA
    _ChildB --> _ChildBA
    style _ChildAA stroke:#080,stroke-width:4px
    end
    subgraph ne_peut_pas_lire*
    direction TB
    __Main --> __ChildA
    __Main --> __ChildB
    __ChildA --> __ChildAA
    __ChildB --> __ChildBA
    style __Main stroke:#800,stroke-width:4px
    style __ChildB stroke:#800,stroke-width:4px
    style __ChildA stroke:#800,stroke-width:4px
    style __ChildBA stroke:#800,stroke-width:4px
    style __ChildAA stroke:#080,stroke-width:4px
    end
end
```

*Le cas 2 ne peut être lu si un seul des droits rouges est Vrai dans ce rôle.

#### Ecriture

Ici, le droit est moins permissif. ChildA permet de créer un accès à un Role qui contient uniquement les droits des enfants directs.

Nous aurons ainsi :

```mermaid
flowchart TD
subgraph _
    subgraph admin
    direction TB
    Main --> ChildA
    Main --> ChildB
    ChildA --> ChildAA
    ChildAA --> ChildAAA
    ChildB --> ChildBA
    style ChildA stroke:#088,stroke-width:4px
    style ChildB stroke:#088,stroke-width:4px
    end
    subgraph peut_editer
    direction TB
    _Main --> _ChildA
    _Main --> _ChildB
    _ChildA --> _ChildAA
    _ChildAA --> _ChildAAA
    _ChildB --> _ChildBA
    style _ChildBA stroke:#080,stroke-width:4px
    style _ChildAA stroke:#080,stroke-width:4px
    end
    subgraph ne_peut_pas_editer
    direction TB
    _Main_ --> _ChildA_
    _Main_ --> _ChildB_
    _ChildA_ --> _ChildAA_
    _ChildAA_ --> _ChildAAA_
    _ChildB_ --> _ChildBA_
    style _ChildAAA_ stroke:#800,stroke-width:4px
    style _ChildBA_ stroke:#080,stroke-width:4px
    style _ChildAA_ stroke:#080,stroke-width:4px
    style _ChildB_ stroke:#800,stroke-width:4px
    end
end
```

```mermaid
flowchart TD
subgraph _
    subgraph admin
    direction TB
    Main --> ChildA
    Main --> ChildB
    ChildA --> ChildAA
    ChildAA --> ChildAAA
    ChildB --> ChildBA
    style ChildA stroke:#088,stroke-width:4px
    style ChildAA stroke:#088,stroke-width:4px
    end
    subgraph peut_editer
    direction TB
    _Main --> _ChildA
    _Main --> _ChildB
    _ChildA --> _ChildAA
    _ChildAA --> _ChildAAA
    _ChildB --> _ChildBA
    style _ChildAA stroke:#080,stroke-width:4px
    style _ChildAAA stroke:#080,stroke-width:4px
    end
end
```

On conserve le cas particulier d'un droit n'ayant pas de parent :

```mermaid
flowchart TD
subgraph _
    subgraph admin
    direction TB
    Main --> ChildA
    Main --> ChildB
    ChildA --> ChildAA
    ChildAA --> ChildAAA
    ChildB --> ChildBA
    style Main stroke:#088,stroke-width:4px
    end
    subgraph peut_editer
    direction TB
    _Main --> _ChildA
    _Main --> _ChildB
    _ChildA --> _ChildAA
    _ChildAA --> _ChildAAA
    _ChildB --> _ChildBA
    style _ChildB stroke:#080,stroke-width:4px
    style _Main stroke:#080,stroke-width:4px
    style _ChildA stroke:#080,stroke-width:4px
    end
    subgraph ne_peut_pas_editer
    direction TB
    _Main_ --> _ChildA_
    _Main_ --> _ChildB_
    _ChildA_ --> _ChildAA_
    _ChildAA_ --> _ChildAAA_
    _ChildB_ --> _ChildBA_
    style _Main_ stroke:#080,stroke-width:4px
    style _ChildA_ stroke:#080,stroke-width:4px
    style _ChildB_ stroke:#080,stroke-width:4px
    style _ChildAA_ stroke:#800,stroke-width:4px
    style _ChildAAA_ stroke:#800,stroke-width:4px
    style _ChildBA_ stroke:#800,stroke-width:4px
    end
end
```


#### Cas particulier de right_read_users

right_read_users devrait être attribuable/attribué avec n'importe quel Role pouvant gérer un accès qui lui-même gère un accès.

Ceci est vrai pour **Lecture** et **Ecriture**.

Exemple :

```mermaid
classDiagram
class ChildA {
  right_edit
  right_read
}
class ReadUsers {
  right_read_users
}
Main --> ChildA
Main --> ReadUsers
ChildA --> ChildAA
ChildAA --> ChildAAA
```

```mermaid
flowchart TD
subgraph _
    subgraph admin
    direction TB
    Main --> ChildA
    Main --> ReadUsers
    ChildA --> ChildAA
    ChildAA --> ChildAAA
    style ChildA stroke:#088,stroke-width:4px
    end
    subgraph peut_gerer
    direction TB
    _Main --> _ChildA
    _Main --> _ReadUsers
    _ChildA --> _ChildAA
    _ChildAA --> _ChildAAA
    style _ChildAA stroke:#080,stroke-width:4px
    style _ReadUsers stroke:#080,stroke-width:4px
    end
    subgraph ne_peut_toujours_pas_gerer*
    direction TB
    __Main --> __ChildA
    __Main --> __ReadUsers
    __ChildA --> __ChildAA
    __ChildAA --> __ChildAAA
    style __ChildAAA stroke:#800,stroke-width:4px
    style __ReadUsers stroke:#080,stroke-width:4px
    end
end
```

*car ChildAAA n'est pas vivible sans __ChildAA

Mais :

```mermaid
flowchart TD
subgraph _
    subgraph admin
    direction TB
    Main --> ChildA
    Main --> ReadUsers
    ChildA --> ChildAA
    ChildAA --> ChildAAA
    style ChildAA stroke:#088,stroke-width:4px
    end
    subgraph ne_peut_pas_gerer
    direction TB
    _Main --> _ChildA
    _Main --> _ReadUsers
    _ChildA --> _ChildAA
    _ChildAA --> _ChildAAA
    style _ChildAAA stroke:#080,stroke-width:4px
    style _ReadUsers stroke:#800,stroke-width:4px
    end
end
```

Car ChildAAA ne permet pas de gérer d'autres accès.


### Traitement du cas avec périmètres

Considérons un modèle un petit peu plus complet :

```mermaid
classDiagram
class Main {
  right_manage
}
class ChildA {
  right_manage_inf_levels
  right_manage_same_levels
}
class ChildAA {
  rightA
}
class ChildB {
  right_manageB
}
class ChildBA {
  rightB
}
Main --> ChildA
Main --> ChildB
ChildA --> ChildAA
ChildB --> ChildBA

PerimCentrale --> Hopital1
PerimCentrale --> Hopital2
Hopital2 --> Unite1
```

Lorsqu'un groupe de droits ne possède pas de inf/same level, cela veut dire que sont right_manage est valable sur TOUS les périmètres.

Nous pouvons avoir des cas comme ceci :

```mermaid
flowchart TD
subgraph _
direction TB
    
    subgraph admin
        direction LR
        subgraph Hop2
            direction TB
            Main --> ChildA_same_lvl
            Main --> ChildB
            ChildA_same_lvl --> ChildAA
            ChildB --> ChildBA
            style ChildA_same_lvl stroke:#088,stroke-width:4px
        end
        subgraph any
            direction TB
            Main_ --> ChildA_
            Main_ --> ChildB_
            ChildA_ --> ChildAA_
            ChildB_ --> ChildBA_
            style ChildB_ stroke:#088,stroke-width:4px
        end
        Hop2 --- any
    end

    direction LR
    subgraph peut lire si Hop2
    direction TB
    _Main --> _ChildA
    _Main --> _ChildB
    _ChildA --> _ChildAA
    _ChildB --> _ChildBA
    style _ChildAA stroke:#080,stroke-width:4px
    style _ChildBA stroke:#080,stroke-width:4px
    end
    subgraph ne peut pas lire si Hop3
    direction TB
    __Main --> __ChildA
    __Main --> __ChildB
    __ChildA --> __ChildAA
    __ChildB --> __ChildBA
    style __ChildBA stroke:#080,stroke-width:4px
    style __ChildAA stroke:#800,stroke-width:4px
    end
end
```


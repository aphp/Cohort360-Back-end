<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#model">Modèle de données</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

**Cohort360-Back-end** serves as the backend of two main web applications: _Portail_ & _Cohort360_.
_Portail_ aims to allow controlling accesses to EDS (Entrepôts de Données de Santé) data.

The main functionalities are to allow:
* Users to give access to other users over patient nominative or pseudonymised data 
* Users to allow other users to give these accesses
* Cohort360 users to ask for exports of their cohorts and download them as CSV files or transfer them to Jupyter 
workspaces
* Admins to manage Jupyter and Unix workspaces

### Built With

Here is a list of major frameworks used here.
* [Django](https://www.djangoproject.com)
* [Django REST Framework](https://www.django-rest-framework.org/)
* [PosgreSQL](https://www.postgresql.org/)
* [Redis](https://redis.io/)
* [Celery](https://docs.celeryproject.org/en/stable/)
* [DRF-YASG (Swagger Generator)](https://drf-yasg.readthedocs.io/en/stable/)


<!-- GETTING STARTED -->
## Getting Started
_The following guide is valid for Unix like platforms. Another guide will be available soon for Windows users_

### Prerequisites

* Python (_version 3.11_)
  ```sh
  sudo apt-get update
  sudo apt-get install python3.11
  ```
If you already have a different version of Python installed, consider adding the _deadsnakes_ repo:
```sh
sudo apt update && sudo apt upgrade
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 -y
python3.11 --version
```
  
* PostgreSQL
  ```sh
  sudo apt-get install postgresql postgresql-contrib
  ```
* Install python3.11-dev:
    ```sh
    sudo apt-get install python3.11-dev
    ```
* Kerberos authentication development library
  ```sh
  sudo apt-get install -y libkrb5-dev gcc
  ```

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/aphp/Cohort360-Back-end.git
   cd Cohort360-Back-end
   ```
2. Prepare a virtual environment
   ```sh
   pip install virtualenv
   virtualenv -p python3.11 venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
    If you are using proxy, it can be necessary to add it in pip install:
    ```shell
    pip install --proxy http://my-proxy:proxy-port -r requirements.txt
    ```


3. Prepare your database
- 3.1. Enter _psql_ interactive shell
   ```sh
   sudo -u postgres psql
   ```
- 3.2. Create a user and a database and grant all privileges
   ```psql
   CREATE USER portail_dev_limited_rw PASSWORD 'portail_psswd';
   CREATE DATABASE portail_dev OWNER portail_dev_limited_rw;
   GRANT ALL PRIVILEGES ON DATABASE portail_dev TO portail_dev_limited_rw;
   \q
   ```
4. Configuration : 
- create a **.env** file (admin_cohort/.env) following **admin_cohort/.env.example** format

5. Django migrations files are already included per application. Next, run migrations to create the database tables
   ```sh
   source venv/bin/activate
   python manage.py migrate
   ```

7. Insert few data rows so that the whole application could work (adapt with your email address, and the 
PERIMETER_TYPES you provide in _admin_cohort/.env_ file):
  ```psql
    \c portail_dev
    -- An admin user
    INSERT INTO "user" (firstname , lastname, provider_id, provider_username, email) 
                VALUES ('Admin', 'ADMINSON', 1, '96214', 'admin.adminson@c360.co');
    INSERT INTO accesses_profile (id, user_id, source, is_active, firstname, lastname, email) 
                          VALUES (1, '96214', 'Manual', 't', 'admin', 'ADMIN', 'admin.adminson@c360.co');

    -- An simple user to play with
    INSERT INTO "user" (firstname , lastname, provider_id, provider_username, email) 
                VALUES ('Simple', 'SIMPLSON', 2, '41269', 'simple.simplson@c360.cc');
    INSERT INTO accesses_profile (id, user_id, source, is_active, firstname, lastname, email) 
                          VALUES (2, '41269', 'Manual', 't', 'Simple', 'SIMPLSON', 'simple.simplson@c360.co');

    -- Basic perimeters tree
    INSERT INTO accesses_perimeter (id, name, source_value, short_name, local_id, type_source_value, parent_id) 
                            VALUES (1, 'APHP', 'Assistance Publique - Hôpitaux de Paris', 'AP-HP', 'Local 00', 'AP-HP', null),
                                   (2, 'Hopit 1', 'Hopital 01', 'Hopit 1', 'Local 01','Hopital', 1),
                                   (3, 'Hopit 2', 'Hopital 02', 'Hopit 2', 'Local 02','Hopital', 1),
                                   (4, 'Unit 1', 'Unité 01', 'Unit 1', 'Hopital 2', 'Unit', 2);

    -- Full administration role
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
                         VALUES(1,'FULL_ADMIN','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t',
                                't','t','t','t','t','t','t','t','t','t','t','t');
    -- Attribute admin role to admin profile
    INSERT INTO accesses_access (role_id, perimeter_id, profile_id) VALUES (1, 1, 1);
  ```
8. If you want to start using Cohort360:
  ```psql
    \c portail_dev
    -- Nominative Data reading role
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
                        VALUES (2,'Nominative Patient Reader','f','f','f','f','f','f','f','f','f','f','f','f','t','f',
                                'f','f','f','f','f','f','f','f','f','f','f','f','f','f','f','f');
    -- Pseudo-anonymised Data reading role
    INSERT INTO accesses_role (id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users, 
                               right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level, 
                               right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels, 
                               right_manage_data_accesses_same_level, right_read_data_accesses_same_level, 
                               right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels, 
                               right_read_patient_nominative, right_search_patient_with_ipp, 
                               right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs, 
                               right_export_csv_nominative, right_export_csv_pseudo_anonymised, 
                               right_manage_export_csv, right_manage_review_export_csv, 
                               right_manage_review_transfer_jupyter, right_manage_transfer_jupyter, 
                               right_review_export_csv, right_review_transfer_jupyter, 
                               right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised, 
                               right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users) 
                       VALUES (3,'Pseudo-anonymised Patient Reader','f','f','f','f','f','f','f','f','f','f','f','f','f',
                               'f','t','f','f','f','f','f','f','f','f','f','f','f','f','f','f','f');

    -- Access to NominativeDataReader for User Admin ADMIN on Hospital 1
    INSERT INTO accesses_access (role_id, perimeter_id, profile_id) VALUES(2, 1, 1);
  ```
## Testing
In order to allow Django to run its tests, authorise database user _portail_dev_limited_rw_ to create a test database
  ```sh
    sudo -u postgres psql
  ```
  ```psql
  ALTER USER portail_dev_limited_rw CREATEDB;
  ```
Activate your virtual environment (if it's not)
  ```sh
  source venv/bin/activate
  ```
Run: `python manage.py test`

<!-- USAGE EXAMPLES -->
## Usage

In the initial way to use this back-end server, authentication should be made using connection to _APHP JWT_'s server.

If you want to use it fully locally, update `admin_cohort/AuthMiddleware.py` file.

Run the server to start making request via `localhost:8000`:
```sh
source venv/bin/activate
python manage.py runserver
```
Open the browser on `localhost:8000/docs` for more details on the API.

## Data Models

In order to explore models in a Python console, launch the following command in your virtual environment.
```sh
source venv/bin/activate
```
```
python manage.py shell
```

Import models:
```
>> from accesses.models import Access, Profile, Role
```

You can start exploring your data models:
```
>> all_profiles = Profile.objects.all()
>> first_profile = all_profiles .first()
>> first_profile.provider_id
```

<!-- CONTRIBUTING -->
<!-- ## Contributing

1. Clone the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request with develop branch -->

## How to deploy this application to your infrastructure

The following files contains AP-HP-specific code. You'll need to write your own implementation of the methods and
replace
them in your CI/CD pipeline.

1. [conf_perimeters](accesses/conf_perimeters.py)
2. [conf_auth](admin_cohort/conf_auth.py)
3. [conf_cohort_job_api](cohort/conf_cohort_job_api.py)
4. [conf_exports](exports/conf_exports.py)
5. [conf_workspaces](workspaces/conf_workspaces.py)

<!-- CONTACT -->

## Contact

open-source@cohort360.org

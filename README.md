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

Portail has the aim of controlling the access to EDS (Entrepôts de Données de Santé) data

The main goals are to allow:
* Users to give access to other users to patient nominative or pseudonymised data 
* Users to allow other users to give these accesses
* Cohort360 users to ask for exports of their cohorts and download them as CSV files or transfer them to Jupyter workspaces
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

### Prerequisites

* Python
  ```sh
  sudo apt-get update
  sudo apt-get install python3.8
  ```
* PostgreSQL
  ```sh
  sudo apt-get install postgresql postgresql-contrib
  ```
* Kerberos authentication development library
  ```sh
  sudo apt-get install -y libkrb5-dev gcc
  ```

### Installation

1. Clone the repo
   ```sh
   git clone https://gitlab.eds.aphp.fr/dev/console-admin/admin-back-end.git
   cd admin-back-end
   ```
2. Prepare a virtual environment
   ```sh
   pip install virtualenv
   virtualenv -p python3.8 venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Prepare your database
   ```sh
   sudo -u postgres psql
   ```
   ```psql
   CREATE USER portail_dev_limited_rw PASSWORD 'portail_psswd';
   CREATE DATABASE portail_dev OWNER portail_dev_limited_rw;
   \q
   ```
4. Configuration : 
- Complete your admin_cohort/.env file following .env.example format
- Clone, in each app folder `accesses`, `cohort`, `exports`, `workspaces`, the _example.conf_ file removing _example._.
- Complete these files with your own process.
5. Now run Django migrations in that order
   ```sh
   source venv/bin/activate
   python manage.py migrate
   ```
6. In order to allow Django to run its tests, authorise the user to create a test database
  ```sh
    sudo -u postgres psql
  ```
  ```psql
  ALTER USER portail_dev_limited_rw CREATEDB;  
  ```
7. If you want to run the server locally to try your own new actions, you'll need to give your user access to the schemas
  ```pqsl
    \c portail_dev
    GRANT ALL PRIVILEGES ON DATABASE portail_dev TO portail_dev_limited_rw;
  ```
8. Also, here are a few rows to add so that the whole model could work (adapt with your email address, and the PERIMETER_TYPES you provide in .env):
  ```psql
    \c portail_dev
    -- An admin user
    INSERT INTO "user" (firstname , lastname, provider_id, provider_username, email) VALUES('Cid', 'Kramer', 0, '96214', 'cid.kramer@garden.bal');
    INSERT INTO profile(id, user_id, source, is_active, firstname, lastname, email) VALUES(0, '96214', 'Manual', 't', 'Cid', 'Kramer', 'cid.kramer@garden.bal');

    -- An simple user to play with
    INSERT INTO "user" (firstname , lastname, provider_id, provider_username, email) VALUES('Squall', 'Leonheart', 1, '41269', 'squall@garden.bal');
    INSERT INTO profile(id, user_id, source, is_active, firstname, lastname, email) VALUES(1, '41269', 'Manual', 't', 'Squall', 'Leonheart', 'squall@garden.bal');

    -- Basic perimeter tree
    INSERT INTO portail_care_site(id, name, type_source_value, parent_id) 
    VALUES 
        (0, 'AP-HP', 'AP-HP', null),
        (1, 'Hospital 1', 'Hospital', 0),
        (2, 'Hospital 2', 'Hospital', 0),
        (3, 'Unit 1', 'Hospital', 2)
    ;

    -- Full administration role
    INSERT INTO role(id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users, right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level, right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels, right_manage_data_accesses_same_level, right_read_data_accesses_same_level, right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels, right_read_patient_nominative, right_search_patient_with_ipp, right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs, right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv, right_manage_review_export_csv, right_manage_review_transfer_jupyter, right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter, right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised, right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users) VALUES(0,'FULL_ADMIN','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t','t');
    -- Access to admin profile
    INSERT INTO access(role_id, perimeter_id, profile_id) VALUES(0, 0, 1);
  ```
9. If you want to start using Cohort:
  ```psql
    \c portail_dev
    -- Nominative Data reading role
    INSERT INTO role(id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users, right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level, right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels, right_manage_data_accesses_same_level, right_read_data_accesses_same_level, right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels, right_read_patient_nominative, right_search_patient_with_ipp, right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs, right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv, right_manage_review_export_csv, right_manage_review_transfer_jupyter, right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter, right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised, right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users) VALUES(1,'Nominative Patient Reader','f','f','f','f','f','f','f','f','f','f','f','f','t','f','f','f','f','f','f','f','f','f','f','f','f','f','f','f','f','f');
    -- Pseudo-anonymised Data reading role
    INSERT INTO role(id, name, right_edit_roles, right_add_users, right_edit_users, right_read_users, right_manage_admin_accesses_same_level, right_read_admin_accesses_same_level, right_manage_admin_accesses_inferior_levels, right_read_admin_accesses_inferior_levels, right_manage_data_accesses_same_level, right_read_data_accesses_same_level, right_manage_data_accesses_inferior_levels, right_read_data_accesses_inferior_levels, right_read_patient_nominative, right_search_patient_with_ipp, right_read_patient_pseudo_anonymised, invalid_reason, right_read_logs, right_export_csv_nominative, right_export_csv_pseudo_anonymised, right_manage_export_csv, right_manage_review_export_csv, right_manage_review_transfer_jupyter, right_manage_transfer_jupyter, right_review_export_csv, right_review_transfer_jupyter, right_transfer_jupyter_nominative, right_transfer_jupyter_pseudo_anonymised, right_manage_env_unix_users, right_manage_env_user_links, right_read_env_unix_users) VALUES(2,'Pseudo-anonymised Patient Reader','f','f','f','f','f','f','f','f','f','f','f','f','f','f','t','f','f','f','f','f','f','f','f','f','f','f','f','f','f','f');

    -- Access to NominativeDataReader for User 1 on Hospital1
    INSERT INTO access(role_id, perimeter_id, profile_id) VALUES(1, 1, 1);
  ```

<!-- USAGE EXAMPLES -->
## Usage

In the initial way to use this back-end server, authentication should be made using connection to APHP jwt server.

If you want to use it fully locally, update `admin_cohort/AuthMiddleware.py` file.

Run the server to start making request via `localhost:8000`:
```sh
source venv/bin/activate
python manage.py runserver
```
You can now go on website `localhost:8000/docs/` for more details on the API.

## Testing

Run: `python manage.py test`

<!-- CONTRIBUTING -->
## Contributing

1. Clone the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request with develop branch


<!-- CONTACT -->
## Contact

Alexandre Martin, main developer - [@alexandreMartinEcl](https://gitlab.eds.aphp.fr/alexandreMartinEcl) - alexandre.martin3@aphp.fr

Julien Dubiel, project Owner - [@j.du](https://gitlab.eds.aphp.fr/j.du) - julien.dubiel@aphp.fr

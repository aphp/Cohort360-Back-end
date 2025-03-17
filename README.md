<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<div align="center">
<img src="admin_cohort/static/admin_cohort/img/logo_cohort360.png" alt="Logo" width="300" height="114">

# Cohort360 Backend
<br />

[![Actions Status](https://github.com/aphp/Cohort360-Back-end/workflows/main/badge.svg)](https://github.com/aphp/Cohort360-Back-end/actions)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=aphp_Cohort360-Back-end&metric=alert_status)](https://sonarcloud.io/dashboard?id=aphp_Cohort360-Back-end)
![image](https://img.shields.io/badge/Python-3.12-blue/?color=blue&logo=python&logoColor=9cf)
![image](https://img.shields.io/badge/Django-5.0-%2344b78b/?color=%2344b78b&logo=django&logoColor=green)
<br />
<a href="https://github.com/aphp/Cohort360-Back-end/issues/new">Report a bug</a>
·
<a href="CHANGELOG.md">What's new ?</a>
</div>

---

<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#overview">Overview</a>
      <ul>
        <li><a href="#features">Features</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#project-setup">Project Setup</a>
      <ul>
        <li><a href="#get-the-code">Get the code</a></li>
        <li><a href="#configuration">Configuration</a></li>
        <li><a href="#environment-variables">Environment variables</a></li>
        <li><a href="#setup">Setup</a></li>
      </ul>
    </li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>



## Overview

**Cohort360-Back-end** serves as the backend of two main web applications: [**Cohort360**](https://github.com/aphp/Cohort360) & [**Portail**](https://github.com/aphp/Cohort360-AdministrationPortal).  
📌 **Portail** is to be open-sourced later this year.

### 🔑 Features

- Multiple authentication modes: OIDC & JWT
- Role & Perimeter based access management
- **Cohort360**'s requests versioning and cohort creation
- Real-time updates using web sockets
- Email-based notifications
- Manage data exports workflows; data can be exported in multiple formats: CSV, XLSX and Hive
- Web content management
- User impersonating for issues diagnosis
- Caching
- ...

<div align="right">
  ⬆️ <a href="#readme-top">back to top</a>
</div>

### 🛠️ Built With

* [Django](https://www.djangoproject.com)
* [Django REST Framework](https://www.django-rest-framework.org/)
* [DRF-spectacular](https://drf-spectacular.readthedocs.io/en/latest/)
* [PosgreSQL](https://www.postgresql.org/)
* [Redis](https://redis.io/)
* [Celery](https://docs.celeryproject.org/en/stable/)


## 🚀 Project setup

### 1. 📥 Get the code

   ```sh
   git clone https://github.com/aphp/Cohort360-Back-end.git
   ```

### 2. 🔧 Configuration

  ▶️ Create a **.env** file in the _admin_cohort_ directory following the **.setup/.env.example** template  
  🔆 More insights on the used environment variables below.
   ```sh
   cp .setup/.env.example admin_cohort/.env
   ```
  ▶️  Create a **perimeters.csv** file in the _.setup_ directory following the **.setup/perimeters.example.csv** format
   ```sh
   cp .setup/perimeters.example.csv .setup/perimeters.csv
   ```
### 3. 📋 Environment variables

#### 🔷 System
<details>
  <summary>Admin user account</summary>

  For demo purposes, an admin account is needed to be created with basic fields

  | Variable        | Description           | Default Value    |
  |-----------------|-----------------------|------------------|
  | ADMIN_USERNAME  | Used as `login`       | admin            |
  | ADMIN_FIRSTNAME | Admin user first name | Admin            |
  | ADMIN_LASTNAME  | Admin user last name  | ADMIN            |
  | ADMIN_EMAIL     | Admin email address   | admin@backend.fr |

</details>

<details>
  <summary>Basic</summary>

  | Variable              | Description                                                                                                                                                                              | Default Value                                                          |
  |-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
  | INCLUDED_APPS         | comma-separated apps names                                                                                                                                                               | accesses,cohort_job_server,cohort,exporters,exports,content_management |
  | DEBUG                 | boolean to enable/disable debug mode                                                                                                                                                     | False                                                                  |
  | ADMINS                | List of admin users to notify for errors. <br/>Used by the _django.utils.log.AdminEmailHandler_ <br/>Multi-value variable ex: `Admin1,admin1@backend.fr;Admin2,admin2@backend.fr`        |                                                                        |
  | NOTIFY_ADMINS         | A boolean to allow sending `ADMINS` email notifications                                                                                                                                  | False                                                                  |
  | FRONT_URL             | Cohort360 frontend URL                                                                                                                                                                   | http://local-cohort.fr                                                 |
  | FRONT_URLS            | comma-separated frontend URLs. if defined, it must include the `FRONT_URL`                                                                                                               | http://local-portail.fr,http://local-cohort.fr                         |
  | BACK_URL              | The backend URL without the _http_ schema                                                                                                                                                | localhost:8000                                                         |
  | CELERY_BROKER_URL     | Broker URL                                                                                                                                                                               | redis://localhost:6379                                                 |
  | CELERY_RESULT_BACKEND | Broker URL                                                                                                                                                                               | redis://localhost:6379                                                 |
  | SOCKET_LOGGER_HOST    | Host URL to which the logs will be sent, logs are currently sent to a Network SocketHandler (see the [reference](https://docs.python.org/3/library/logging.handlers.html#sockethandler)) | localhost                                                              |
  | USERNAME_REGEX        | A regex to validate users usernames                                                                                                                                                      | (.*)                                                                   |
  | EMAIL_REGEX_CHECK     | A regex to validate email addresses                                                                                                                                                      | ^[\w.+-]+@[\w-]+\.[\w]+$                                               |

</details>

#### 🔷 Databases

<details>
  <summary>Databases</summary>

  The backend connects to a main database `DB_AUTH_NAME` where the app data is persisted.
  An extra database connection is used to retrieve _OMOP_ related data.

  | Variable         | Description          | Default Value  |
  |------------------|----------------------|----------------|
  | DB_AUTH_NAME     |                      | cohort_db      |
  | DB_AUTH_USER     |                      | cohort_dev     |
  | DB_AUTH_PASSWORD |                      | cohort_dev_pwd |
  | DB_AUTH_HOST     |                      | localhost      |
  | DB_AUTH_PORT     |                      | 5432           |
  | DB_OMOP_SCHEMA   | Annexe database name |                |
  | DB_OMOP_NAME     |                      |                |
  | DB_OMOP_HOST     |                      |                |
  | DB_OMOP_USER     |                      |                |
  | DB_OMOP_PASSWORD |                      |                |
  | DB_OMOP_PORT     |                      |                |

</details>

#### 🔷 Authentication
<details>
  <summary>Authentication modes</summary>

  The backend supports 2 authentication modes:
   * Based on an external API exposing specific routes (for example an API that connects to an LDAP server under the hood)  
        - By setting `ENABLE_JWT` to **True**
        - Users log in using their credentials _username_/_password_
   * OIDC authentication using one or multiple OIDC servers.
        - By setting `ENABLE_JWT` to **False**
        - You can configure a new server by adding extra variables: `OIDC_AUTH_SERVER_2`, `OIDC_REDIRECT_URI_2` ...

  | Variable               | Description                                                                                                                                                                                                              | Default Value            |
  |------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------|
  | ENABLE_JWT             | Allow the backend to authenticate requests with a JWT token. <br/>Requests must include the <br/>`HTTP_AUTHORIZATIONMETHOD` header with value `JWT` (matches `JWT_AUTH_MODE` in [settings.py](admin_cohort/settings.py)) | True                     |
  | JWT_ALGORITHMS         | comma-separated algorithms used to decode JWT tokens                                                                                                                                                                     | RS256,HS256              |
  | ID_CHECKER_URL         | If set, the backend uses this URL to check users identity                                                                                                                                                                | None                     |
  | OIDC_AUDIENCE          | comma-separated values of audience                                                                                                                                                                                       | audiences_1,audiences_2  |
  | OIDC_AUTH_SERVER_1     |                                                                                                                                                                                                                          | server_1                 |
  | OIDC_REDIRECT_URI_1    |                                                                                                                                                                                                                          | redirect_uri_1           |
  | OIDC_CLIENT_ID_1       |                                                                                                                                                                                                                          | client_id_1              |
  | OIDC_GRANT_TYPE_1      | The authentication flow in the backend supports only `authorization_code` for now                                                                                                                                        | authorization_code       |
  | OIDC_CLIENT_SECRET_1   |                                                                                                                                                                                                                          | client_secret_1          |
  | OIDC_EXTRA_SERVER_URLS | comma-separated URLs of other OIDC servers issuing tokens for users                                                                                                                                                      |                          |

</details>



#### 🔷 Apps related environment variables

<details>
  <summary>Cohort</summary>

  | Variable              | Description                                                                                                                                                             | Default Value         |
  |-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------|
  | LAST_COUNT_VALIDITY   | Validity of a Cohort Count Request in hours                                                                                                                             | 24                    |
  | COHORT_LIMIT          | Maximum patients a "small" cohort can contain ("small" cohorts will be run right away while big ones can be launched manually by calling Django API on the /? endpoint) | 20000                 |
  | SJS_URL               | SJS URL ex: https://sjs.aphp.fr (il s'agit de l'url du serveur [QueryExecutor](https://github.com/aphp/Cohort360-QueryExecutor))                                        |                       |
  | SJS_USERNAME          | The system user of the SJS app. Used to make _patch_ calls on Cohorts and DatedMeasures                                                                                 |                       |
  | ETL_USERNAME          | The system user of the ETL app. Used to make _patch_ calls on Cohorts                                                                                                   |                       |
  | META_SECURITY_PSEUDED | Security mode used to access FHIR resources                                                                                                                             | meta.security=PSEUDED |
  | USE_SOLR              | A boolean to indicate if a SolR database is used. If so, FHIR criteria are translated to SolR format                                                                    | False                 |
  | FHIR_URL              | The URL of the server used to translate FHIR criterias to SolR format, ex: https://fhir.aphp.fr                                                                         |                       |

</details>

<details>
  <summary>Perimeters</summary>

  | Variable                  | Description                                                                     | Default Value |
  |---------------------------|---------------------------------------------------------------------------------|---------------|
  | PERIMETER_TYPES           | comma-separated types of perimeters                                             |               |
  | ROOT_PERIMETER_ID         | ID of the root perimeter                                                        |               |
  | REPORTING_PERIMETER_TYPES | comma-separated types of perimeters to include in the `FeasibilityStudy` report |               |

</details>

<details>
  <summary>Data Exports</summary>

  The backend comes with three exporters allowing to have data exported in the following formats:
    * CSV
    * XLSX
    * To a Hive database
  
  | Variable                    | Description                                                                    | Default Value |
  |-----------------------------|--------------------------------------------------------------------------------|---------------|
  | STORAGE_PROVIDERS           | comma-separated URLs of servers to store exported data                         |               |
  | EXPORT_API_URL              | URL of the third-party API that handles exports                                |               |
  | EXPORT_TASK_STATUS_ENDPOINT | The endpoint allowing to check _export job_ status                             |               |
  | EXPORT_CSV_PATH             | Path to the directory where CSV exports are stored                             |               |
  | EXPORT_XLSX_PATH            | Path to the directory where XLSX exports are stored                            |               |
  | DAYS_TO_KEEP_EXPORTED_FILES | Days to keep exported data available for download                              | 7             |
  | INFRA_API_URL               | URL of the third-party API that handles creating the database for Hive exports |               |
  | HIVE_DB_FOLDER              | Path to the directory where the Hive database is stored                        |               |
  | CREATE_DB_ENDPOINT          | The endpoint allowing to _create_ a Hive database                              |               |
  | ALTER_DB_ENDPOINT           | The endpoint allowing to _change ownership_ of a Hive database                 |               |
  | HADOOP_TASK_STATUS_ENDPOINT | The endpoint allowing to check _database creation job_ status                  |               |
  | HIVE_EXPORTER_USER          | Name of the system user that creates Hive databases                            |               |
  | DISABLE_TERMINOLOGY         | boolean to disable exported data translation                                   | False         |

</details>

#### 🔷 Email alerts

<details>
  <summary>Accesses expiry alters</summary>
  
  | Variable                           | Description                                              | Default Value |
  |------------------------------------|----------------------------------------------------------|---------------|
  | ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS  | Number of days for first alert about accesses to expire  | 30            |
  | ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS | Number of days for second alert about accesses to expire | 2             |
  | ACCESS_MANAGERS_LIST_LINK          | A URL link to a file with the list of accesses managers  |               |

</details>

#### 🔷 Scheduled jobs

<details>
  <summary>Custom periodic tasks</summary>

  | Variable                                | Description                                                                                                   | Default Value                                                                                                                                    |
  |-----------------------------------------|---------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|  
  | LOCAL_TASKS                             | `;` separated tasks with execution time <br /> in the format of _task name,module,function name,hour,minutes_ | count_users_on_perimeters,accesses.tasks.count_users_on_perimeters,5,30;<br/>check_expiring_accesses,accesses.tasks.check_expiring_accesses,6,0  |
  | MAINTENANCE_PERIODIC_SCHEDULING_MINUTES | Frequency of the task to check if a _maintenance job_ is ON                                                   | 1                                                                                                                                                |

</details>

#### 🔷 Security

<details>
  <summary>Secrets and tokens</summary>
  
  | Variable                | Description                                                            | Default Value |
  |-------------------------|------------------------------------------------------------------------|---------------|
  | DJANGO_SECRET_KEY       | Will be set on `SECRET_KEY` in settings.py                             |               |
  | ID_CHECKER_TOKEN_HEADER | Authorization header used by the Identity checker server               |               |
  | ID_CHECKER_TOKEN        | Identity checker server API-key                                        |               |
  | SJS_TOKEN               | SJS API-key                                                            |               |
  | ETL_TOKEN               | ETL API-key                                                            |               |
  | JWT_SIGNING_KEY         | Key used to sign JWT tokens if JWT auth mode is enabled (`ENABLE_JWT`) |               |
  | INFLUXDB_DJANGO_TOKEN   | InfluxDB API-key                                                       |               |

</details>

#### 🔷 Miscellaneous

<details>
  <summary>Emailing system</summary>
  
  | Variable              | Description                               | Default Value |
  |-----------------------|-------------------------------------------|---------------|
  | EMAIL_USE_TLS         |                                           | True          |
  | EMAIL_HOST            |                                           |               |
  | EMAIL_PORT            |                                           |               |
  | EMAIL_SENDER_ADDRESS  | Email address of sender                   |               |
  | EMAIL_SUPPORT_CONTACT | Email address to contact the support team |               |

</details>

<details>
  <summary>Caching responses</summary>

  The backend uses _RedisCache_ from the **django_redis** package.  
  Extra tuning parameters to control cache validity are defined in settings.py

  | Variable     | Description                   | Default Value |
  |--------------|-------------------------------|---------------|
  | ENABLE_CACHE | Enable caching HTTP responses | False         |
  
</details>

<details>
  <summary>Monitoring with InfluxDB</summary>

  To monitor response time of the API, you can configure an InfluxDB connection.  
  :: this activates a new middleware on top of the existing ones to track requests process time.

  | Variable         | Description       | Default Value |
  |------------------|-------------------|---------------|
  | INFLUXDB_ENABLED |                   | False         |
  | INFLUXDB_URL     |                   |               |
  | INFLUXDB_ORG     | Organization name |               |
  | INFLUXDB_BUCKET  | Bucket name       |               |

</details>


### 4. Setup

   🔶 Note that the _setup.sh_ script needs root privileges to run some commands

   ```sh
   bash .setup/setup.sh
   ```
  All set up 🎉  
  
* The development server is running at on port `8000` and the Swagger UI for endpoints documentation is found at: [localhost:8000/docs](http://localhost:8000/docs)
* Once on the Swagger UI, start by getting an authentication **token** by logging in using the `/auth/login/` endpoint. Use that token for 
  authorization on Swagger UI.

<div align="right">
  ⬆️ <a href="#readme-top">back to top</a>
</div>

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed process about contributing to this repository.

## 📜 License

This project is licensed under the Apache License - see the [LICENSE](LICENSE) file for details.

## 💬 Contact

If you find this project useful, please consider starring the repository and report any encountered bugs or issues.  
Write to us at: **open-source@cohort360.org**

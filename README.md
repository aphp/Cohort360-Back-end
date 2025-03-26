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


## Overview

**Cohort360-Backend** serves as the backend of two main web applications: [**Cohort360**](https://github.com/aphp/Cohort360) & [**Portail**](https://github.com/aphp/Cohort360-AdministrationPortal).  

#### 🔑 Features

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

#### 🛠️ Built With

* [Django](https://www.djangoproject.com)
* [Django REST Framework](https://www.django-rest-framework.org/)
* [DRF-spectacular](https://drf-spectacular.readthedocs.io/en/latest/)
* [PosgreSQL](https://www.postgresql.org/)
* [Redis](https://redis.io/)
* [Celery](https://docs.celeryproject.org/en/stable/)

---

## 📚 Project modules & environment variables

<details>
  <summary>🔹System</summary>

  | Variable              | Description                                                                                                                                                                     | Default Value                                                          | Required ?                      |
  |-----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|---------------------------------|
  | DJANGO_SECRET_KEY     | Assigned to Django's `SECRET_KEY` in [settings.py](admin_cohort/settings.py)                                                                                                    |                                                                        | `yes`                           |
  | INCLUDED_APPS         | comma-separated apps names to consider by Django registry                                                                                                                       | accesses,cohort_job_server,cohort,exporters,exports,content_management | no                              |
  | DEBUG                 | boolean to enable/disable debug mode                                                                                                                                            | False                                                                  | no                              |
  | ADMINS                | List of admin users to notify for errors. Used by Django's _AdminEmailHandler_ <br/>Multi-value variable ex: `Admin1,admin1@backend.fr;Admin2,admin2@backend.fr`                |                                                                        | no                              |
  | NOTIFY_ADMINS         | A boolean to allow sending error email notifications to `ADMINS`                                                                                                                | False                                                                  | no                              |
  | FRONTEND_URL          | **Cohort360** frontend URL                                                                                                                                                      | http://local-cohort.fr                                                 | `yes` if the frontend is up     |
  | FRONTEND_URLS         | comma-separated frontend URLs. if defined, it must include the `FRONTEND_URL`                                                                                                   | http://local-portail.fr,http://local-cohort.fr                         | `yes` if the frontend is up     |
  | BACKEND_HOST          | The backend host without the _http_ schema                                                                                                                                      | localhost:8000                                                         | `yes` if different than default |
  | CELERY_BROKER_URL     | Broker URL                                                                                                                                                                      | redis://localhost:6379                                                 | `yes` if different than default |
  | SOCKET_LOGGER_HOST    | Host URL to which the logs will be sent.<br/>Logs are currently sent to a [Network SocketHandler](https://docs.python.<br/>org/3/library/logging.handlers.html#sockethandler)   | localhost                                                              | no                              |

</details>
 
<details>
  <summary>🔹Database</summary>

  The backend uses a main database `DB_NAME` where its data is persisted.  

  | Variable         | Description | Default Value  | Required ? |
  |------------------|-------------|----------------|------------|
  | DB_HOST          |             | localhost      | `yes`      |
  | DB_PORT          |             | 5432           | `yes`      |
  | DB_NAME          |             | cohort_db      | `yes`      |
  | DB_USER          |             | cohort_dev     | `yes`      |
  | DB_PASSWORD      |             | cohort_dev_pwd | `yes`      |

</details>

<details>
  <summary>🔹Authentication</summary>

  The backend uses _Json Web Tokens_ to authenticate requests.

  | Variable       | Description                                          | Default Value | Required ? |
  |----------------|------------------------------------------------------|---------------|------------|
  | JWT_ALGORITHMS | comma-separated algorithms used to decode JWT tokens | RS256,HS256   | `yes`      |

  It supports 2 authentication modes:

   * Authentication using credentials _username/password_ (`default`)  
     For this, **Cohort360-backend** tries validating user credentials in the following order:
        1. If an external identity server/API is configured, use it.
        2. Otherwise, fall back to inplace validation i.e. check if user is registered in database and has provided the correct password
     
     > The external identity server/API may be for example an API that connects to an LDAP server under the hood.  
       This **requires** setting the following variables:
  
      | Variable                           | Description                                                                                | Default Value   | Required ? |
      |------------------------------------|--------------------------------------------------------------------------------------------|-----------------|------------|
      | IDENTITY_SERVER_AUTH_ENDPOINT      | Authentication endpoint on the identity server/API. Ex: https://id-server.com/authenticate |                 | `yes`      |
      | IDENTITY_SERVER_AUTH_TOKEN         | Secret token used to authenticate requests to the identity server/API                      |                 | `yes`      |
      | IDENTITY_SERVER_USER_INFO_ENDPOINT | An endpoint on the identity server/API that returns user info. Used when creating new user |                 | no         |
      | IDENTITY_SERVER_AUTH_HEADER        | Name of the authorization header to include in the request headers                         | _Authorization_ | no         |

   * OIDC authentication using one or multiple OIDC servers (`optional`)
        - By setting `ENABLE_OIDC_AUTH` to **True** (defaults to _False_)
        - Note that **Cohort360-backend** supports only `authorization_code` [grant type](https://auth0.com/docs/get-started/applications/application-grant-types#available-grant-types) for now

  | Variable               | Description                                                         | Default Value | Required ? |
  |------------------------|---------------------------------------------------------------------|---------------|------------|
  | OIDC_AUTH_SERVER_1     |                                                                     |               | `yes`      |
  | OIDC_REDIRECT_URI_1    |                                                                     |               | `yes`      |
  | OIDC_CLIENT_ID_1       |                                                                     |               | `yes`      |
  | OIDC_CLIENT_SECRET_1   |                                                                     |               | `yes`      |
  | OIDC_AUDIENCE          | comma-separated values of audience if multiple                      |               | `yes`      |
  | OIDC_EXTRA_SERVER_URLS | comma-separated URLs of other OIDC servers issuing tokens for users |               | no         |

  > You can configure a new server by adding extra variables: `OIDC_AUTH_SERVER_2`, `OIDC_REDIRECT_URI_2` ...

</details>

<details>
  <summary>🔹Cohort</summary>

  The **Cohort** app mainly allows to process _Cohort Count Requests_ and _Cohort Creation Requests_  
  It uses a [Solr](https://solr.apache.org/) database to store the IDs of patients included in a cohort and to request patients data based on different criteria 
  
  ### Cohort Count Request

  <img src=".docs/img/count_flow.png" alt="count-flow" width="1243" height="1010">
  
  ### Cohort Creation Request

  **Cohort360-backend** can manage creating cohorts according to the number of included patients:  
  * If cohort size is within `COHORT_SIZE_LIMIT`:  it gets created almost instantly
  * Otherwise, it can take up to 24h to be ready as the process of creating it involves doing data indexation Solr wise.  
    The `Solr ETL` entity then makes a callback to **Cohort360-backend** to patch the cohort with its final status (_created_ or _failed_)

  #### 1. If cohort_size < `COHORT_SIZE_LIMIT`

  <img src=".docs/img/create_flow_1.png" alt="create-flow-1" width="1243" height="1010">

  #### 2. If cohort_size > `COHORT_SIZE_LIMIT`

  <img src=".docs/img/create_flow_2.png" alt="create-flow-2" width="1243" height="1010">


  | Variable                | Description                                                                                                                         | Default Value | Required ?          |
  |-------------------------|-------------------------------------------------------------------------------------------------------------------------------------|---------------|---------------------|
  | FHIR_URL                | The URL of the server used to translate FHIR criteria to Solr format, ex: https://fhir.aphp.fr                                      |               | `yes`               |
  | QUERY_EXECUTOR_URL      | ex: https://query-executor.aphp.fr. the URL of your instance of [QueryExecutor](https://github.com/aphp/Cohort360-QueryExecutor)    |               | `yes`               |
  | QUERY_EXECUTOR_USERNAME | The system user of the QueryExecutor app. Used to make _patch_ calls on **Cohorts** and **Count Requests**                          |               | `yes`               |
  | QUERY_EXECUTOR_TOKEN    | Query Executor application API-key                                                                                                  |               | `yes`               |
  | USE_SOLR                | A boolean to indicate if a Solr database is used. If so, FHIR criteria are translated to Solr format                                | False         | no                  |
  | SOLR_ETL_USERNAME       | The system user of the Solr ETL app. Used to make _patch_ calls on Cohorts                                                          |               | `yes` if `USE_SOLR` |
  | SOLR_ETL_TOKEN          | ETL application API-key                                                                                                             |               | `yes` if `USE_SOLR` |
  | TEST_FHIR_QUERIES       | Weather to test queries before sending them to **QueryExecutor**                                                                    | False         | no                  |
  | LAST_COUNT_VALIDITY     | Validity of a _Count Request_ in hours. Passed this period, the request result becomes obsolete and the request must be re-executed | 24            | no                  |
  | COHORT_SIZE_LIMIT       | Maximum patients a "small" cohort can contain ("small" cohorts are created right away while big ones can take up to 24h)            | 20000         | no                  |

</details>

<details>
  <summary>🔹Perimeters</summary>

  **Cohort360-backend** relies on a tree-like structure of perimeters to which users are granted accesses.  
  Perimeters can be of different types (CHU, Hospital, Unit Service ...) and the structure as a whole must have a single parent perimeter.  
  
  | Variable                  | Description                                                                     | Default Value     | Required ? |
  |---------------------------|---------------------------------------------------------------------------------|-------------------|------------|
  | PERIMETER_TYPES           | comma-separated types of perimeters                                             |                   | `yes`      |
  | ROOT_PERIMETER_ID         | ID of the root (parent) perimeter                                               |                   | `yes`      |
  | REPORTING_PERIMETER_TYPES | comma-separated types of perimeters to include in the `FeasibilityStudy` report | `PERIMETER_TYPES` | no         |

    
  Optionally, perimeters can be synced if retrieved from an external database.  
  For this, add **accesses_perimeters** to `INCLUDED_APPS` and set up a second database connection with the following variables: 

  > A periodic task is provided in the  [**accesses_perimeters**](accesses_perimeters/tasks.py) app for this purpose.  
    cf `SCHEDULED_TASKS` for configuration bellow.  
    
  | Variable                      | Description                  | Default Value | Required ? |
  |-------------------------------|------------------------------|---------------|------------|
  | PERIMETERS_SOURCE_DB_HOST     |                              |               | `yes`      |
  | PERIMETERS_SOURCE_DB_PORT     |                              |               | `yes`      |
  | PERIMETERS_SOURCE_DB_NAME     |                              |               | `yes`      |
  | PERIMETERS_SOURCE_DB_USER     |                              |               | `yes`      |
  | PERIMETERS_SOURCE_DB_PASSWORD |                              |               | `yes`      |
  | PERIMETERS_SOURCE_DB_SCHEMAS  | comma-separated schema names | _public_      | no         |

</details>

<details>
  <summary>🔹Data Exports</summary>

  If the **exporters** app is in `INCLUDED_APPS`, the backend will allow to have data exported in the 
  following formats:
  * CSV files
  * XLSX files
  * To a Hive database

  For this, the following variables are required:
  
  | Variable                    | Description                                                                  | Default Value | Required ? |
  |-----------------------------|------------------------------------------------------------------------------|---------------|------------|
  | STORAGE_PROVIDERS           | comma-separated URLs of servers to store exported data                       |               | `yes`      |
  | EXPORT_API_URL              | URL of the third-party API that handles exports                              |               | `yes`      |
  | EXPORT_CSV_PATH             | Path to the directory where CSV exports are stored                           |               | `yes`      |
  | EXPORT_XLSX_PATH            | Path to the directory where XLSX exports are stored                          |               | `yes`      |
  | HADOOP_API_URL              | URL of a third-party API that handles creating the database for Hive exports |               | `yes`      |
  | HIVE_DB_PATH                | Path to the directory where the Hive database is stored                      |               | `yes`      |
  | HIVE_USER                   | Name of the system user that creates Hive databases                          |               | `yes`      |
  | DISABLE_DATA_TRANSLATION    | If True, it disables translating exported data. Export data as is            | False         | no         |
  | DAYS_TO_KEEP_EXPORTED_FILES | Number of days to keep exported data available for download                  | 7             | no         |

</details>

<details>
  <summary>🔹Scheduled tasks</summary>

  **Cohort360-backend** uses Celery's [Periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html) to run scheduled tasks.  
  > cf: `CELERY_BEAT_SCHEDULE` in [settings.py](admin_cohort/settings.py)
  

  | Variable         | Description                                                                                                     | Default Value | Required ? |
  |------------------|-----------------------------------------------------------------------------------------------------------------|---------------|------------|  
  | SCHEDULED_TASKS  | `;` separated tasks configurations in the following format:<br /> _task_name,module,function_name,hour,minutes_ |               | no         |

</details>

<details>
  <summary>🔹Emailing system</summary>

  To enable sending emails, Django's _EmailBackend_ needs the following parameters:
  
  | Variable              | Description                               | Default Value | Required ? |
  |-----------------------|-------------------------------------------|---------------|------------|
  | EMAIL_USE_TLS         |                                           | True          | `yes`      |
  | EMAIL_HOST            |                                           |               | `yes`      |
  | EMAIL_PORT            |                                           |               | `yes`      |
  | DEFAULT_FROM_EMAIL    | Email address of sender                   |               | `yes`      |
  | EMAIL_SUPPORT_CONTACT | Email address to contact the support team |               | no         |

</details>

<details>
  <summary>🔹Email alerts for expiring accesses</summary>

  **Cohort360-backend** allows to frequently check users accesses validity and send email notifications for how to renew them.  
  To enable this behaviour, include the [_check_expiring_accesses_](accesses/tasks.py) task in `SCHEDULED_TASKS`.  
  > By default, two emails are sent `30` and `2` days respectively before accesses expiry date.

  | Variable                           | Description                                         | Default Value | Required ? |
  |------------------------------------|-----------------------------------------------------|---------------|------------|
  | ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS  | Send first email X days before accesses expire      | 30            | no         |
  | ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS | Send second email X days before accesses expire     | 2             | no         |
  | ACCESS_MANAGERS_LIST_LINK          | A link to a file with the list of accesses managers |               | no         |

</details>

<details>
  <summary>🔹Misc</summary>
  
  <details>
    <summary> Regex</summary>
  
  You can set optional regular expressions to validate usernames and email addresses

  | Variable       | Description                         | Default Value            | Required ? |
  |----------------|-------------------------------------|--------------------------|------------|
  | USERNAME_REGEX | A regex to validate usernames       | (.*)                     | no         |
  | EMAIL_REGEX    | A regex to validate email addresses | ^[\w.+-]+@[\w-]+\.[\w]+$ | no         |
  
  </details>
  
  <details>
    <summary> Caching responses</summary>
  
  The backend uses _RedisCache_ from the **django_redis** package.  
  Extra tuning parameters to control cache validity are defined in [settings.py](admin_cohort/settings.py)

  | Variable     | Description                   | Default Value | Required ? |
  |--------------|-------------------------------|---------------|------------|
  | ENABLE_CACHE | Enable caching HTTP responses | False         | no         |
    
  </details>

  <details>
    <summary> Store diagnosis data on InfluxDB</summary>
  
  You can configure an InfluxDB connection to store response times of the API endpoints and plug in a monitoring tool like Grafana.  
  > this activates a new middleware on top of the existing ones to track requests process time.

  Start by adding the variable `INFLUXDB_ENABLED` set to **True** in addition to the following: 
  
  | Variable              | Description         | Default Value | Required ? |
  |-----------------------|---------------------|---------------|------------|
  | INFLUXDB_URL          | InfluxDB server URL |               | `yes`      |
  | INFLUXDB_ORG          | Organization name   |               | `yes`      |
  | INFLUXDB_BUCKET       | Bucket name         |               | `yes`      |
  | INFLUXDB_DJANGO_TOKEN | InfluxDB API-key    |               | `yes`      |
  
  </details>
</details>

<div align="right">
  ⬆️ <a href="#readme-top">back to top</a>
</div>

---

## 🚀 Project setup

### 1. 📥 Get the code

   ```sh
   git clone https://github.com/aphp/Cohort360-Back-end.git
   ```

### 2. 🔧 Configuration

  1. Create a **.env** file in the _admin_cohort_ directory following the **.setup/.env.example** template  
  🔆 More insights on environment variables above.
   ```sh
   cp .setup/.env.example admin_cohort/.env
   ```

  2. Create a **perimeters.csv** file in the _.setup_ directory following the **.setup/perimeters.example.csv** format
   ```sh
   cp .setup/perimeters.example.csv .setup/perimeters.csv
   ```

### 3. Setup

   🔶 Note that the _setup.sh_ script needs root privileges to run some commands

   ```sh
   bash .setup/setup.sh
   ```
  All set up 🎉  
  
* The development server is running on port `8000` and the Swagger UI for endpoints documentation is found at: [localhost:8000/docs](http://localhost:8000/docs)
* Once on the Swagger UI, start by getting an authentication **token** by logging in using the `/auth/login/` endpoint. Use that token for 
  authorization.

<div align="right">
  ⬆️ <a href="#readme-top">back to top</a>
</div>

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed process about contributing to this repository.

## 📜 License

This project is licensed under the Apache License - see the [LICENSE](LICENSE) file for details.

## 💬 Contact

If you find this project useful, please consider starring the repository and report any encountered bugs or issues.  
Write to us at: **open-source@cohort360.org**

<div align="right">
  ⬆️ <a href="#readme-top">back to top</a>
</div>
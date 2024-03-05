![image](https://img.shields.io/badge/Python-3.11-blue/?color=blue&logo=python&logoColor=9cf)
![image](https://img.shields.io/badge/Django-4.1-%2344b78b/?color=%2344b78b&logo=django&logoColor=green)

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

### PROJECT SETUP
===============================================================
===============================================================  /!\ maybe group all in one file   ===================================================
===============================================================
1. Clone the repo
   ```sh
   git clone https://github.com/aphp/Cohort360-Back-end.git
   cd Cohort360-Back-end
   chmod +x .setup/*.sh
   ```
2. Install prerequisites
   Switch to **root** user and install prerequisites
   ```sh
   sudo -s
   bash .setup/prerequisites.sh
   ```
3. Prepare a virtual environment
   ```sh
   exit
   bash .setup/virtualenv.sh
   ```

4. Prepare your database
   ```sh
   bash .setup/setup_db.sh
   ```

5. Configuration
- Create a **.env** file (admin_cohort/.env) following **.setup/.env.example** format

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
2. [conf_auth](admin_cohort/auth/utils.py)
3. [conf_cohort_job_api](cohort/services/conf_cohort_job_api.py)
4. [conf_exports](exports/conf_exports.py)
5. [conf_workspaces](workspaces/conf_workspaces.py)

<!-- CONTACT -->

## Contact

open-source@cohort360.org

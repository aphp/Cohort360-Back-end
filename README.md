[![Actions Status](https://github.com/aphp/Cohort360-Back-end/workflows/main/badge.svg)](https://github.com/aphp/Cohort360-Back-end/actions)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=aphp_Cohort360-Back-end&metric=alert_status)](https://sonarcloud.io/dashboard?id=aphp_Cohort360-Back-end)
![image](https://img.shields.io/badge/Python-3.11-blue/?color=blue&logo=python&logoColor=9cf)
![image](https://img.shields.io/badge/Django-5.0-%2344b78b/?color=%2344b78b&logo=django&logoColor=green)

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
      <a href="#project-setup">Project Setup</a>
      <ul>
        <li><a href="#get-the-code">Get the code</a></li>
        <li><a href="#configuration">Configuration</a></li>
        <li><a href="#setup">Setup</a></li>
      </ul>
    </li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#deployment-on-local-infrastructure">Deployment on local infrastructure</a></li>
    <li><a href="#contributing">Contributing</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About the project

**Cohort360-Back-end** serves as the backend of two main web applications: **Portail** & [**Cohort360**](https://github.com/aphp/Cohort360).  
**Portail** provides capabilities to manage and control access to EDS data (Entrepôts de Données de Santé).

The main functionalities are:
* Allow users to give access to other users over patient nominative or pseudonymized data. 
* Provide users with managing roles in order to allow other users to control accesses.
* Allow **Cohort360** users to export their cohorts and download them in CSV format or transfer them to Jupyter 
workspaces.
* Allow admins to manage Jupyter workspaces

### Built With

Here is a list of major frameworks used here.
* [Django](https://www.djangoproject.com)
* [Django REST Framework](https://www.django-rest-framework.org/)
* [PosgreSQL](https://www.postgresql.org/)
* [Redis](https://redis.io/)
* [Celery](https://docs.celeryproject.org/en/stable/)
* [DRF-YASG (Swagger Generator)](https://drf-yasg.readthedocs.io/en/stable/)


<!-- GETTING STARTED -->

## Project setup
### 1. Get the code
   ```sh
   git clone https://github.com/aphp/Cohort360-Back-end.git
   ```

### 2. Configuration
   * Create a **.env** file in the _admin_cohort_ directory following the **.setup/.env.example** format  
   * Create a **perimeters.csv** file in the _.setup_ directory following the **.setup/perimeters.example.csv** format


### 3. Setup
   ```sh
   cd Cohort360-Back-end/.setup
   chmod +x setup.sh
   bash setup.sh
   ```
* Server running at: `localhost:8000`
* API details at: `localhost:8000/docs`


## Deployment on local infrastructure

coming soon


<!-- CONTRIBUTING -->
## Contributing

1. Clone the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request with _main_ branch


<!-- CONTACT -->

## Contact

open-source@cohort360.org

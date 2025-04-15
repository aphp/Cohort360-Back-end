# Changelog

All notable changes to this project will be documented in this file.

## [3.26.0] - 2025-03-18

### 🚀 Features

- Add filters and ordering on Requests
- *(cms)* Add new content management application (#452)
- *(accesses)* Add retrieving accesses within child perimeters
- Add retry failed exports (#454)
- *(users)* Add active user filter (#455)
- *(cohorts)* Add more ordering options
- Add filters to Folders view
- *(cohortcount)* Add new details count mode option (#459)

### 🐛 Bug Fixes

- Make sample ratio optional (#447)
- Handle null values for ExportTable (#448)
- *(exports)* Sort by status (#450)
- Refresh Kerberos auth ticket (#451)
- Add fields to queryset and fix cohorts serializer (#453)
- Set cron job to refresh Kerberos ticket
- Adjust path to Kerberos keytab (#456)
- *(exports)* Typo in param name
- *(exports)* Overwrite export database
- Cron job and fail fast for Hive exports (#457)
- *(exports)* Adjust serializers and urls
- *(email notifs)* Fix path to templates
- *(datedmeasure)* Send extra result to ws
- Update perimeters (#461)
- *(release)* Set tags pattern and fix script

### 🚜 Refactor

- Serializers in Cohort app (#444)
- *(maintenance)* Add new maintenance view sort and filter cap
- Externalize email templates (#458)
- Embedded JWT authentication (#460)

### ⚙️ Miscellaneous Tasks

- Update CHANGELOG.md and bump version to 3.26.0-dev

### Dep

- Bump Django to 5.0.13

## [3.25.11] - 2025-02-28

### 🚜 Refactor

- *(maintenance)* Add new maintenance view sort and filter cap

## [3.25.10] - 2025-02-27

### 🐛 Bug Fixes

- *(exports)* Overwrite export database

## [3.25.9] - 2025-02-27

### Build

- Set version 3.25.9

## [3.25.8] - 2025-02-26

### 🚀 Features

- Add retry failed exports

## [3.25.7] - 1014-02-25

### 🚀 Features

- *(cms)* Add new content management application (#452)

## [3.25.6] - 2025-02-25

### 🐛 Bug Fixes

- Set cron job to refresh Kerberos ticket

## [3.25.5] - 2025-02-24

### 🐛 Bug Fixes

- *(cohort)* Add fields to queryset and fix serializers

## [3.25.4] - 2025-02-24

### Build

- *(docker)* Refresh Kerberos ticket

## [3.25.3] - 2025-02-21

### 🐛 Bug Fixes

- *(exports)* Sort by status

## [3.25.2] - 2025-02-13

### 🐛 Bug Fixes

- Handle null inputs for export table

## [3.25.1] - 2025-02-12

### 🐛 Bug Fixes

- *(cohort)* Handle null value for modeOptions
- *(cohort)* Handle null value for modeOptions
- Adjust CohortResult serializer

### Build

- Set version 3.26.0-dev

## [3.25.0] - 2025-02-12

### 🚀 Features

- Add request migration script 1.6.0
- New payload for exports
- *(logging)* Readd default console logger
- Add configurable socket logger host for gunicorn
- *(auth)* Cache oidc issuer certs (#433)
- *(perimeterUpdate)* Update query snapshot perimeter on perimeter cohort id change (#432)
- *(Swagger)* Add more conf to Swagger UI
- Add multiple deletion for cohort and requests
- *(exports)* Add pivot options
- Cohort sampling (#437)

### 🐛 Bug Fixes

- New export serializer
- Add info to logs (#426)
- *(logger)* Listen 0.0.0.0 for socket logger
- Sonar cloud checks
- *(maintenance)* Message on deletion and prevent sooner ending (#428)
- *(exports)* Check if cohort exists before export
- Parse url as string
- *(exports)* Update export param
- *(exports)* Handle exceptions on calling the Export API
- *(exports)* Auto generate fhir filters only when given source cohort (#435)
- Cache OIDC server certs
- *(pyproject)* Set Python version 3.12.3
- Missing argument for decorator causing DM status to not be updated (#438)
- Small fixes regarding global DMs, exports and logs (#439)
- *(Dockerfile)* Ensure log dir is created
- Improve response time phase 1 (#440)
- *(nginx)* Update static files location
- *(Swagger)* Remove broken setting
- Add configurable link for template (#441)
- *(exports)* Typo in param name
- *(exports)* Include non-null params only
- *(exports)* Check cohort ID for each export table
- *(middleware)* Check InfluxDB setting
- *(exports)* Add terminology setting
- Sort DatedMeasures within a RequestSnapshot (#443)
- *(perimeters)* Distinct user count for inferior levels (#445)
- Remove auth token logging
- Count users on perimeters (#446)

### 🚜 Refactor

- Rm dead code
- Get cohort ids in v2
- Work with new exports payload
- *(start)* [**breaking**] Add new docker entrypoint options (#427)
- Use the new DE API within exports (#429)
- Remove gitlab ci
- Genral refactorization (#431)
- Clean Dockerfile (#436)
- *(exports)* Update params

### 📚 Documentation

- Update changelog

### ⚡ Performance

- Optimize DB queries

### 🧪 Testing

- *(exports)* Fix test
- Fix typo
- Mock Celery task call
- *(exports)* Typo in argument name
- Add tests for counting users on perimeters
- *(perimeters)* Fix assertions

### ⚙️ Miscellaneous Tasks

- Enable sonarcloud scan
- Upgrade actions versions
- Remove sonar result as dependency of publishing docker
- Fix sonar
- Fix GH Actions
- Add version suffix in pyproject
- Set test env vars
- Set test env vars before migrating DB
- Automate making releases
- Automate making releases

### Build

- Introduce uv and reduce project deps
- Set version to "x.y.z-dev" format
- Fix permissions over cron
- Fix Dockerfile

### Deps

- Add coverage
- Bump the json logger package

## [3.24.1] - 2024-11-21

### 🚀 Features

- Add new fhir perimeter sync app (#405)
- Add type and message to maintenance phase (#416)
- *(maintenance)* Add ws event for started and ended maintenance phases (#418)
- Add user info in log records (#422)
- Add request migration script 1.6.0

### 🐛 Bug Fixes

- Adjust CohortRights serializer (#407)
- Hotfix 3.23.2, check user is not anonymous (#408)
- Hotfix 3.23.3 to get perimeters from snapshots (#409)
- Hotfix 3.23.4 impersonate users (#410)
- *(swagger)* Remove clientSecret setting
- *(static)* Remove old static files
- Hotfix 3.23.5 exports (#411)
- *(exports)* Hotfix 3.23.7 notifs and files extensions (#413)
- Hotfix 3.23.8 exports in one file (#414)
- Hotfix 3.23.9 downloading xlsx/csv exports (#415)
- Fhir perimeter source type + django max request line
- *(cohort)* USE_SOLR boolean matching
- Plug in actual cohort operators
- Feasibility study serializers
- *(exports)* Set file extension to .zip
- Add traceId header
- Remove extra arg
- *(exports)* Do not create sub-cohort for measurement table
- *(migrationscripts)* Add resource type to filter + fix basic resource postprocess
- *(migrationscript)* Add fix request migration script
- Hotfix 3.23.16 xlsx exports right verif (#424)
- *(accesses)* Get only perimeters with defined rights

### 🚜 Refactor

- *(ws)* Move websocket manager to main module (#417)
- Settings per app config (#420)
- Update download url and add serializers
- Always download a zip file

### 📚 Documentation

- Update changelog

### ⚙️ Miscellaneous Tasks

- Set version 3.24.0-SNAPSHOT
- Get project version from settings

## [3.23.10] - 2024-09-02

### 🐛 Bug Fixes

- Increase Gunicron's request line limit
- *(cohort)* USE_SOLR boolean matching

## [3.23.9] - 2024-08-23

### 🐛 Bug Fixes

- *(exports)* File downloading

## [3.23.8] - 2024-08-22

### 🐛 Bug Fixes

- *(exports)* Set file extension if grouped tables

## [3.23.7] - 2024-08-21

### 🐛 Bug Fixes

- *(exports)* Dynamically set file extension

## [3.23.6] - 2024-08-21

### 🐛 Bug Fixes

- Allow downloading XLSX exports

## [3.23.5] - 2024-08-20

### 🐛 Bug Fixes

- *(exports)* Adjust serializers and enable XLSX notifs
- Adjust CohortRights serializer (#407)
- Hotfix 3.23.2, check user is not anonymous (#408)
- Hotfix 3.23.3 to get perimeters from snapshots (#409)
- Hotfix 3.23.4 impersonate users (#410)
- *(swagger)* Remove clientSecret setting
- *(static)* Remove old static files
- *(celery)* Adjust run command

### ⚙️ Miscellaneous Tasks

- Set version 3.24.0-SNAPSHOT
- Get project version from settings

## [3.23.4] - 2024-08-14

### 🐛 Bug Fixes

- *(exports)* Adjust export serializer
- Load post auth hooks

## [3.23.3] - 2024-08-14

### 🐛 Bug Fixes

- Get perimeters from cohorts snapshots

## [3.23.2] - 2024-08-14

### 🐛 Bug Fixes

- *(permissions)* Check request user is not anonymous

## [3.23.1] - 2024-08-13

### 🐛 Bug Fixes

- *(cohort)* Adjust cohort rights serializer

## [3.23.0] - 2024-08-13

### 🚀 Features

- Add encounterdaterangelist query patch (#388)
- *(querymigration)* Add filter migration (#394)
- *(exports)* Force create cohort subsets
- *(queryupdater)* Add static filter conditions
- *(auth)* [**breaking**] Allow multiple auth with multiple oidc issuers (#404)
- Schedule requests refreshing (#397)
- *(docs)* Add drf spectacular #1179 (#402)

### 🐛 Bug Fixes

- *(admin_cohort)* Track logins via OIDC
- Hotfix 3.22.2 to flag snapshots of subcohorts (#390)
- Hotfix 3.22.3 flag snapshots of subcohort (#391)
- *(logging)* Stop error notifications
- *(exports)* Encode filter's values
- Hotfix 3.22.6 add export xlsx conf (#396)
- *(accesses)* Remove deprecated tasks decorator
- *(accesses)* Typo in argument name
- *(accesses)* Use regular QuerySet instead of raw SQL
- *(cohort)* Return the correct request update time
- Hotfix 3.22.8 Check read rights with mode min max (#401)
- *(roles)* Set page number pagination
- *(entrypoint)* Kinit fails silently
- *(auth)* Use client id instead of oidc issuer url to find config
- *(OIDC)* Properly set audience
- *(OIDC)* Add test env vars
- Bump Gunicorn to 23.0.0
- *(filters)* Ignore auto generated filters

### 🚜 Refactor

- Check users identity (#384)
- *(celery)* Remove beats from docker entry point
- *(accesses)* Add new accesses_perimeters app (#398)
- *(accesses)* Filter perimeters directly without FactRelationship mapper
- *(cohort)* Remove perimeters retriever (#403)
- More configurable launch options and settings (#399)

### 🧪 Testing

- *(exports)* Add tests to exports service
- *(accesses)* Remove redundant tests

### ⚙️ Miscellaneous Tasks

- Add ubuntu package update
- Get image tag from settings
- *(GH Actions)* Get image tag from settings 2
- Set version 3.23.0

### Build

- Add latest tag to main docker builds

## [3.22.0] - 2024-07-09

### 🚀 Features

- *(export)* Add xslx export
- *(exports)* Xlsx exporter (#383)
- *(patch)* Add patch for queries to v1.5.0 (#385)

### 🐛 Bug Fixes

- Hotfix 3.21.1 to secure saving/using FHIR filters (#375)
- Hotfix 3.21.2 to exclude cohort subsets in exports nested view queryset (#376)
- Hotfix 3.21.3 for hive exports (#377)
- *(exports)* Hotfix 3.21.4 donwloaded file name (#378)
- *(crb)* Allow all resource name type
- *(WS)* Add failure reason to payload
- *(deps)* Upgrade pyopenssl version
- *(cohort)* Error on cohort creation
- *(cohort)* Fix requests update datetime
- *(cohort)* Set requests update datetime as latest modification of snapshots
- *(exports)* Remove unrecognized argument

### 🚜 Refactor

- *(crb)* Remove solr collection mapping (#380)
- Add cohort auxiliary app for OSS (#373)
- *(cohort)* Fix tests and small bugs
- *(cohort)* Fix code smells

### 🎨 Styling

- Upgrade linter

### 🧪 Testing

- *(folders)* Fix list with filters
- *(cohort)* Disable Folders list with filters test

### ⚙️ Miscellaneous Tasks

- Add test and docker build in github ci (#382)
- *(deps)* Fix libs versions and ignore unpatched ones


## [3.21.0] - 2024-06-05

### 🚀 Features

- *(setup)* Add project setup script (#337)
- *(scriptMigration)* Add new migration script for Condition new codesystem
- *(rights)* Persist rights in db and add new view (#340)
- *(auth)* Add impersonating system (#360)
- *(perimeter)* Add sort by name and id (#371)
- *(pp)* Add full access data reader right (#369)

### 🐛 Bug Fixes

- *(rollout)* Update token variable (#351)
- *(pagination)* Increase page max limit to 30k
- *(rollout)* Reset old token variable
- *(rollout)* Reset old token variable
- *(rollout)* Exclude long pending cohort jobs (#354)
- *(ruff)* Upgrade ruff and update conf
- *(exports)* Properly dump query
- *(exports)* Stringify uuid object
- *(accesses)* Rearrange migrations
- *(Cohort)* Build query to create sub cohort
- *(Cohort)* Add missing properties in cohort query
- *(sub-cohorts)* Pass in missing DatedMeasure for sub cohort
- *(sub-cohorts)* Properly get export associated to sub cohort
- *(cohorts)* Exclude sub-cohorts from the view queryset
- *(profiles)* Fix serializer's fields
- *(cohorts)* Exclude sub-cohorts from the view queryset for ordinary users
- *(WS)* Hotfix 3.20.2, complete cohort metadata (#361)
- Permissions over Users View (#363)
- *(exports-v1)* Control creating sub cohorts for tables
- *(cohort)* Tag cohorts subsets
- *(exporters)* Alter Export API auth tokens
- *(exporters)* Add missing field to serializer and fix tasks
- *(exports)* Manage instances of two exports models
- *(exporters)* Raise error on export failure
- *(exports)* Add migration to populate datalabs table
- *(exports)* Migration to populate datalabs
- Migrate old exports (#366)
- *(exports)* Include exported tables in migration
- *(exports)* Adjust filter fields
- *(exports)* URLs conf
- *(exports)* Fix migration, and remove workspaces env vars
- *(exports)* Fix migration for exports without unix accounts
- *(Exports)* Create sub cohort only when a filter is provided
- *(cohort)* Duplicate DM for cohort subsets
- *(Exports)* Properly format tables input in the export payload
- *(Exports)* Properly format tables input in the export payload
- *(Cohort)* Add resourceType to the cohort subset query
- *(Cohort)* Add resourceType to CohortQuery schema
- *(Cohort)* Disable 2 obsolete tests
- *(Cohort, Exports)* Abort export if cohort subsets fail
- *(Cohort, Exports)* Abort export if cohort subsets fail 2
- *(Exports)* Properly inject resource type to create cohort subsets
- *(Cohort)* Ensure DM associated to a cohort subset has a measure value
- *(Cohort)* Add filterSolr to the cohort subset creation query
- *(Cohort)* Remove suffixed resource type from the cohort subset creation query
- *(exports)* Typo in template reference
- *(cohort-WS)* Update frontend client when patching DM/CR fails
- *(cohort-WS)* Add resource status to the payload
- *(feasibility reports)* Hotfix 3.20.3 (#374)

### 🚜 Refactor

- Remove redundant fields from profile with user (#357)
- Upgrade Django (#359)
- *(exports)* Improve exports v1 #2592 (#362)
- *(exports)* Add new exporters app (#353)
- Standardize exports with new app (#364)
- *(exports)* Remove old models (#367)
- Remove workspaces app (#368)
- Replace CRB with job server (#358)

### 🎨 Styling

- *(cohort)* Remove unused import
- *(perimeters)* Reformat code

### 🧪 Testing

- *(setup)* Add test for loading initial data
- *(rights)* Remove the unexpected argument on function call
- *(exports)* Isolate tests regarding the new exporters app (#365)
- *(cohort)* Test cohort subsets creation
- *(Exports)* Fix tests
- *(Exports)* Add tests
- *(accesses)* Fix tests

### ⚙️ Miscellaneous Tasks

- Back to full pipeline
- *(tests)* Test all

## [3.20.0] - 2024-04-04

### 🚀 Features

- Add Websocket server (#325)
- *(auth-ws)* Set auth for websockets (#331)
- *(RQS-cohorts)* Add resulted cohorts to the RQS reduced serializer
- *(feasibility-studies)* Add report metadata
- Uv replaces pip (#332)
- *(cache)* Use dummy cache when disabled
- *(feasibility-studies)* Update report name
- Add extra_infos to websocket payload (#338)
- *(WS-cohort)* Add extra info for global DM
- *(exports)* Set download URL to frontend (#349)

### 🐛 Bug Fixes

- Check read data rights (#329)
- *(ws)* Add auth for WS and fix tests
- Refresh object from DB to fix lag in Celery tasks (#333)
- Nginx conf
- *(confperimeters)* Add cast to caresite relationship query
- *(cohort)* Pass auth_method for cohort request
- *(auth)* Default to jwt auth method for Swagger
- *(auth)* Return value for third party app users authentication
- *(auth)* Return value for third party app users authentication
- *(Celery)* Lock object inside Celery task
- *(WS)* Authenticate request on handshake
- *(feasibility studies)* Report template
- *(crb)* Decode fhir filter values before querying fhir query translator
- *(feasibility studies)* Change wording case
- *(auth)* Url to refresh token
- *(count-requests)* Lock instance and await for task before update
- *(cache)* Disable caching nested RQSs
- *(auth)* Raise error on invalid credentials
- *(uv)* Activate venv
- *(WS)* Stringify UUID object
- Activate virtual env
- *(Docker)* Activate uv's venv
- *(Docker)* Activate uv's venv
- *(Docker)* Activate uv's venv
- *(WS)* Refresh objects from DB
- *(accesses)* Fix sorting bug (#343)
- *(exports)* Use new DataExporter spec (#344)
- *(exports)* Use new DataExporter spec (#345)
- *(exports)* Use DE new specification (#347)
- *(maintenance)* Allow login via JWT server (#348)
- *(WS)* Add cohort fhir_group_id
- *(exports)* Ensure single cohort for CSV exports
- *(exports)* Fix download URL

### 🚜 Refactor

- Admin cohort app (#327)
- *(ws)* Minor changes on ws payload
- Send WebSocketInfos instead of smaller object (#339)
- *(crb)* Set count to 0 when testing query filters

### 🎨 Styling

- Move asgi.py to cohort_admin
- *(WS)* Add logs
- *(cohort)* Remove logs and make anchor safe
- Remove useless import

### 🧪 Testing

- *(auth)* Forbid auth without token
- Remove mock of websocket for feasibility

### Build

- Add debug tools
- Launch websocket in background before gunicorn
- *(uv)* Introduce uv to Dockerfile (#341)
- *(docker)* Fix docker-entrypoint

## [3.19.0] - 2024-02-14

### 🚀 Features

- *(crb)* Add questionnaire response resource type

### 🐛 Bug Fixes

- *(accesses)* Hotfix 3.17.6 to search among manageable perimeters (#319)
- Hotfix 3.18.2, update emails for feasibility reports (#320)
- Alter feasibility report HTML page title
- *(feasibility study)* Limit reports generation at UFs (#322)
- *(feasibility study)* Add env var for reporting perimeter types (#323)
- *(crb)* Typo in questionnaire reponse enum

### 🚜 Refactor

- Use new table List instead of cohort_definition (#303)
- *(exports)* Externalize services (#321)

## [3.18.0] - 2024-01-18

### 🚀 Features

- Upgrade Django (#306)
- Add feasibility studies (#305)
- *(fhir filters)* Get filters by user id and resource (#307)
- *(accesses)* Include link to accesses managers list in the email notification

### 🐛 Bug Fixes

- Psycopg package name in requirements.txt
- Rm unused imports
- Add env var for tests
- Improve exports v1 (#308)
- *(exports)* Use new statuses from Infra API (#309)
- Pass perimeters ids instead of queryset to check rights
- Hotfix 3.17.1 (#310)
- Spark job request with callback path (#311)
- *(exports)* New statuses
- Hotfix 3.17.2 for right check regression for FHIR (#313)
- *(feasibility_studies)* Fix error on creation
- *(feasibility studies)* Add specific logger
- *(feasibility studies)* Format request input
- *(feasibility studies)* Properly set callbackPath in the SJS payload
- *(feasibility studies)* Report download and notify on success and on error
- *(feasibility studies)* Properly chain tasks
- *(auth)* Remove unnecessary logging on token refresh failure
- Raise raw exception on login error via OIDC
- *(exports)* Hotfix 3.17.3 fix typo in attribute name (#315)
- *(exports)* Hotfix 3.17.3 (#316)
- *(exports)* Hotfix 3.17.4 to remove unused call to infra api (#317)
- *(exports)* Hotfix 3.17.5 remove check user unix account (#318)

### 🚜 Refactor

- Unify urls conf

### 📚 Documentation

- Add changelog (#312)

### 🎨 Styling

- Remove explicit auth backend. to be guessed on the fly

### 🧪 Testing

- *(feasibility_studies)* Add tests
- *(crb)* Fix tests

### ⚙️ Miscellaneous Tasks

- Multi-stage Dockerfile
- Back to full pipeline again
- Remove proxy args

### Build

- Set custom user for container
- Set user root for container

## [3.17.0] - 2023-12-20

### 🐛 Bug Fixes

- Parse fhir_group_ids to get cohort rights
- Remove unique rights combination constraint
- Get user data rights
- Get user data rights on perimeters
- *(perimeters)* Correct cohort_ids type (#302)
- Filter accesses on perimeters for user and deny deleting a used role
- Log request data and params
- Perimeters daily update task

### Lint

- Rm unused imports

## [3.16.15] - 2023-12-12

### 🚀 Features

- *(crb)* Add new imagingStudy resource type (#290)
- Log HTTP requests (#282)
- *(Fhir filters)* Delete multiple filters
- Add new exports flow v1 (#273)
- Use token to activate maintenance for rollout (#298)
- *(cohortrequester)* Add upgrade script for atih code conversion (#296)

### 🐛 Bug Fixes

- *(queryupgrade)* Fix sql + add previous version limit to upgrade + versions recap (#287)
- Manage invalid token errors
- Manage invalid token errors
- *(emailing for exports)* Hotfix 3.16.3 (#288)
- Set main to v3.17.0-SNAPSHOT
- Update export email template
- Adjust user permission to allow users to read their own data
- *(fhir filters)* Get owner_id from request
- *(fhir filters)* Fix serializer and tests
- *(fhir filters)* Make FhirFilter objects user restricted only
- *(fhir filters)* Allow to delete filters
- *(release notes)* Sort data in response, allow patch
- *(querymigration)* Fix code translation + add new v1.4.1 script (#291)
- Hotfix 3.16.6 for queries updater (#292)
- *(requests logs)* For FhirFilters
- Raise specific exception
- *(cohort)* Count requests
- *(cohort)* Format cohort ids for rights checking
- *(fhir filters)* Alter uniqueness rule and remove cache
- *(fhir filters)* Add conditional unique constraint
- *(fhir filters)* Typo in tests
- *(fhir filters)* Linter
- Hotfix 3.16.7 for computing user rights (#293)
- Hotfix 3.16.8 for Exports permissions (#294)
- *(exports new flow)* Resolve conflicts after merge exports new flow v1 PR
- Rqs version incrementing
- *(migrationscript)* Correct mapping script
- *(crb)* Add right check in crb #2401 (#297)
- *(CRB)* Hotfix 3.16.14 crb rights check (#300)

### 🚜 Refactor

- Bring services to cohort app (#276)

### 🧪 Testing

- Fix test for queries updater
- *(requests logs)* Improve coverage
- *(exports new flow)* Improve coverage
- *(exports new flow)* Improve coverage

### Lint

- Rm unused import

## [3.16.0] - 2023-10-13

### 🚀 Features

- *(exports)* Add new models (#266)
- Add views to manage cache (#262)
- *(cohort)* Add new migration script for serialized queries in 1.4.0 (#271)
- Manage release notes and news (#279)
- *(cohort)* Add cohort request builder service (#263)
- *(cohort)* Add cohort request builder service (#263)
- Add console handler for logs in local env, dev and qua
- *(crb)* Add real fhir query test (#285)

### 🐛 Bug Fixes

- Permissions for exports new  views (#267)
- Count users on perimeters (#268)
- Count user on perimeters (#269)
- Fix conflicts after merge
- Fix migration dependency
- Hotfix_3.15.3 accesses on perimeters (#270)
- Review permissions and hide urls in the DRF api view (#272)
- Exports bug fix and emails refactor (#274)
- Attach logo to email signature
- Manage downloading old csv exports (#277)
- Add migration for old release notes
- Move patches to scripts
- *(crb)* Rename serialized model (#280)
- Small changes after merge
- Alter release notes migration
- Upgrade to Django v4.1.11
- *(serializedquery)* Correct field mapping + add medication new mapping (#281)
- Silently log JWT token errors
- *(crb)* Ipp list resource name (#283)
- Extend try catch in crb process + add optional fields to query model
- *(crb)* Correct sjs replacements
- *(crb)* Optional fields for temporal constraints
- *(requestmigration)* Add new param mappings (#284)

### 🚜 Refactor

- Replace YarnReadOnlyViewsetMixin by allowed http methods on views
- Email notification

### 🎨 Styling

- *(RQS queries updater)* Reformat code

### 🧪 Testing

- Fix tests
- Fix tests regarding adjusted permissions
- Fix tests after emails notification refacto
- Add tests for email notifications
- Add tests for email notifications
- Fix sending emails tests

### ⚙️ Miscellaneous Tasks

- *(main)* Up to v3.16.0-SNAPSHOT
- Remove feat_deploy_xxx and release_xxx from workflow rules
- Multi-stage Dockerfile to optimize Docker image
- Fix multi-stage Dockerfile
- Remove multi-stage Dockerfile

## [3.15.0] - 2023-09-05

### ⚙️ Miscellaneous Tasks

- Release 3.15.0 (#265)

## [3.14.1] - 2023-08-09

### 🐛 Bug Fixes

- Hotfix 3.14.1 add cohort name on email subject for export requests (#247)
- Hotfix 3.14.1 cohort name in export email subject (#248)
- Hotfix 3.14.1 cohort name in export email subject (#249)
- Hotfix 3.14.1 cohort name in export email subject (#250)

## [3.14.0] - 2023-08-08

### 🚀 Features

- *(requests)* Send mail to receipients of shared requests (#205)
- *(logging)* Add trace id tag and set logging format to json (#212)
- *(exports)* Add export name to mail subject (#213)
- *(access)* Set default minimum access duration to 2 years
- *(request)* Add param to optionnaly notify user when sharing request
- *(Accesses)* Add created_by and updated_by (#223)
- Add regex to manage service accounts usernames

### 🐛 Bug Fixes

- Add a null check before adding trace id to headers
- Add missing dependency
- *(exports)* Properly pass InfraAPI auth token (#216)
- Set version 3.14.0-SNAPSHOT
- *(exports)* Enable limit on cohorts list for exports (#220)
- Reset cache on request sharing (#225)
- *(cache)* Invalidate cache on request sharing
- Add migration dependency
- *(migration)* Run Python instead of SQL
- *(migration)* Fix dependency
- *(migration)* Fix dependency
- *(cache)* Include request's path in cache key
- *(cache)* Include request params and path in keys (#229)
- Add default values to variables in test env
- Adjust responses on checking profiles
- Log instead of raise error on logout (#231)
- Portail patient OIDC auth (#234)
- Hotfix 3.13.7 notify admins about errors (#236)
- Hotfix 3.13.8 serve static files (#242)
- Hotfix 3.13.9 decode jwt per issuer (#245)

### 📚 Documentation

- Fix missing column of accesses role
- Fix missing column of accesses role; pseudonymised

### ⚙️ Miscellaneous Tasks

- Set dependency check to github pipeline instead of gitlab (#211)
- Add fixed Dockerfile (#218)
- Add workflow to gitlab-ci
- Add workflow to gitlab-ci
- Add workflow to gitlab-ci
- Set back docker.io as images hub instead of Harbor


## [3.13.9](https://github.com/aphp/Cohort360-Back-end/compare/3.13.8...3.13.9) (2023-08-08)


### Bug Fixes

* hotfix_3.13.9 decode oidc tokens per issuer ([#244](https://github.com/aphp/Cohort360-Back-end/issues/244)) ([4b04a22](https://github.com/aphp/Cohort360-Back-end/commit/4b04a2228eda8413766442456fea8bcfdfad6aca))



## [3.13.8](https://github.com/aphp/Cohort360-Back-end/compare/3.13.7...3.13.8) (2023-08-03)


### Bug Fixes

* hotfix 3.13.8 serve static files ([#241](https://github.com/aphp/Cohort360-Back-end/issues/241)) ([2e14048](https://github.com/aphp/Cohort360-Back-end/commit/2e14048d1fdf4fecbcdaff268fa5f5ec6ca6ebb9))



## [3.13.7](https://github.com/aphp/Cohort360-Back-end/compare/3.13.6...3.13.7) (2023-08-02)


### Bug Fixes

* hotfix 3.13.7 notify admins about errors ([#235](https://github.com/aphp/Cohort360-Back-end/issues/235)) ([2e82e7a](https://github.com/aphp/Cohort360-Back-end/commit/2e82e7a6209aad5f47e1ae2b1163423f4962f3ab))



## [3.13.6](https://github.com/aphp/Cohort360-Back-end/compare/3.13.5...3.13.6) (2023-08-02)


### Bug Fixes

* hotfix 3.13.6 oidc auth with portail patients ([#233](https://github.com/aphp/Cohort360-Back-end/issues/233)) ([3696b9b](https://github.com/aphp/Cohort360-Back-end/commit/3696b9b7dbfe594ae6d2f79eef1ccbd80876d525))



## [3.13.5](https://github.com/aphp/Cohort360-Back-end/compare/3.13.4...3.13.5) (2023-08-01)


### Bug Fixes

* log instead of raise error on logout ([#230](https://github.com/aphp/Cohort360-Back-end/issues/230)) ([1924fe2](https://github.com/aphp/Cohort360-Back-end/commit/1924fe2eeacf917f45a6cde3925060d9a8cd8813))



## [3.13.4](https://github.com/aphp/Cohort360-Back-end/compare/3.13.3...3.13.4) (2023-07-27)


### Bug Fixes

* **cache:** include request params and path in keys ([#228](https://github.com/aphp/Cohort360-Back-end/issues/228)) ([299623f](https://github.com/aphp/Cohort360-Back-end/commit/299623f9f9cd17abaf20965e4d065b6074aed56d))
* **cache:** include request path in cache key ([#227](https://github.com/aphp/Cohort360-Back-end/issues/227)) ([59df542](https://github.com/aphp/Cohort360-Back-end/commit/59df5423e7b494ef9f35602ff6fb57765a386fb1))



## [3.13.3](https://github.com/aphp/Cohort360-Back-end/compare/3.13.2...3.13.3) (2023-07-26)


### Bug Fixes

* invalidate cache after bulk transactions ([#222](https://github.com/aphp/Cohort360-Back-end/issues/222)) ([4621199](https://github.com/aphp/Cohort360-Back-end/commit/4621199db0e550bf13ea385e2ebea97f733da80d))
* reset cache after sharing a request ([#226](https://github.com/aphp/Cohort360-Back-end/issues/226)) ([a93a52c](https://github.com/aphp/Cohort360-Back-end/commit/a93a52c99dd5e6b455e9e9f6ef7ffa6dbb267be1))



## [3.13.2](https://github.com/aphp/Cohort360-Back-end/compare/3.13.1...3.13.2) (2023-07-19)


### Bug Fixes

* **exports:** enable limit on cohorts list ([#219](https://github.com/aphp/Cohort360-Back-end/issues/219)) ([61f0990](https://github.com/aphp/Cohort360-Back-end/commit/61f09908f72ce2c93487522d9a83b7e9d2a0c0eb))



## [3.13.1](https://github.com/aphp/Cohort360-Back-end/compare/3.13.0...3.13.1) (2023-07-19)



# [3.13.0](https://github.com/aphp/Cohort360-Back-end/compare/3.12.5...3.13.0) (2023-07-07)


### Bug Fixes

* adjust email text for Hive export ([3972982](https://github.com/aphp/Cohort360-Back-end/commit/397298253c399eb98100e757a9fc8f9f022b22db))
* allow login via OIDc over maintenance phase ([4acf95b](https://github.com/aphp/Cohort360-Back-end/commit/4acf95b41bc041b73cd820c54e965b9049e55f9b))
* alter requests serializer to send RQSs data instead of UUIDs ([#199](https://github.com/aphp/Cohort360-Back-end/issues/199)) ([b295839](https://github.com/aphp/Cohort360-Back-end/commit/b295839ea51c11a18ef44faaa6d90e3075f101e9))
* **auth:** raise exception if user not found ([501a2b8](https://github.com/aphp/Cohort360-Back-end/commit/501a2b8ccabf78892b57f3680dda41834caec2e9))
* **confperimeters:** update compare cohort_id str ([#206](https://github.com/aphp/Cohort360-Back-end/issues/206)) ([7d7245e](https://github.com/aphp/Cohort360-Back-end/commit/7d7245ea3de15e15a508c7394d8437a39ebbaa65))
* fix Gunicorn log handler ([21de7e4](https://github.com/aphp/Cohort360-Back-end/commit/21de7e4a0075a3a6d2ea9096d4337c6cb75a619e))
* forward auth according to auth_method headers ([24b106b](https://github.com/aphp/Cohort360-Back-end/commit/24b106b1c3ea8c712ccfddb77edd4ef84ce603d8))
* login to Swagger ([b00cbcc](https://github.com/aphp/Cohort360-Back-end/commit/b00cbcce34a4ec109090f29d483d0a2cdb543fa3))
* logout user according to auth method headers ([0b828bd](https://github.com/aphp/Cohort360-Back-end/commit/0b828bd80e0e3aa3e151147b8f99319fa7e22a03))
* logout user according to auth method headers ([fe3cf3f](https://github.com/aphp/Cohort360-Back-end/commit/fe3cf3fd5ee424c73e5fe182ff071bfe56656a5b))
* manage request exception on refresh token ([b34e625](https://github.com/aphp/Cohort360-Back-end/commit/b34e625cba15ae135a532cc8402a2f15923efc7e))
* manage Swagger's initial request ([80b51a5](https://github.com/aphp/Cohort360-Back-end/commit/80b51a59b24071c1c9f51396c83e61dd74b47f8c))
* properly retrieve request payload on OIDC login ([001c1e9](https://github.com/aphp/Cohort360-Back-end/commit/001c1e944c6f9ec514454d512dedd1de60ac8b1f))
* retrieve accesses per perimeter ([#193](https://github.com/aphp/Cohort360-Back-end/issues/193)) ([dbe4be9](https://github.com/aphp/Cohort360-Back-end/commit/dbe4be91d707e763a73818564b13798a6122b177))
* send proper HTTP codes in accesses and perimeters responses ([18fa318](https://github.com/aphp/Cohort360-Back-end/commit/18fa318a23f34478b1c4b01859f56d5d02b2e30e))
* send proper response when user not found on OIDC login ([497eda2](https://github.com/aphp/Cohort360-Back-end/commit/497eda2e27f11eae572432594fe6b05eda32875a))
* update Nginx client_max_body_size param ([9ea1a42](https://github.com/aphp/Cohort360-Back-end/commit/9ea1a422eb0dbea05ce56623ce36edf519e91a68))
* verify jwt token signature ([ac50d18](https://github.com/aphp/Cohort360-Back-end/commit/ac50d18e9a5e9aea2b3f6ee58bafd8a43bfac439))


### Features

* add expiring accesses route ([#189](https://github.com/aphp/Cohort360-Back-end/issues/189)) ([9fe4ced](https://github.com/aphp/Cohort360-Back-end/commit/9fe4ced22e772dd4f686b313a36e990323a30f0a))
* add OIDC auth ([#191](https://github.com/aphp/Cohort360-Back-end/issues/191)) ([31db73c](https://github.com/aphp/Cohort360-Back-end/commit/31db73cd38479d4b706321a0bf0147b2b7f7b55a))
* add pagination to the `users within a role` view ([#200](https://github.com/aphp/Cohort360-Back-end/issues/200)) ([da33ac4](https://github.com/aphp/Cohort360-Back-end/commit/da33ac470a361bac932aa16156021b7bf668b23a))
* add patch function to upgrade serialized queries ([#207](https://github.com/aphp/Cohort360-Back-end/issues/207)) ([6ad7bef](https://github.com/aphp/Cohort360-Back-end/commit/6ad7bef682faca5444d37d3eea3b9c58ac982be6))
* add periodic task helper to ensure single run instead of one per django worker ([c261b62](https://github.com/aphp/Cohort360-Back-end/commit/c261b6243dba1bd0ff52b9830ea37f2a29a210e5))
* add version numbers to RQSs and fix old ones in DB ([#201](https://github.com/aphp/Cohort360-Back-end/issues/201)) ([c9f0b27](https://github.com/aphp/Cohort360-Back-end/commit/c9f0b278f87572c85f7e07557df83f04d1463999))
* **role:** add opposing patient role ([#186](https://github.com/aphp/Cohort360-Back-end/issues/186)) ([a4c6310](https://github.com/aphp/Cohort360-Back-end/commit/a4c6310e019c101446e5ff84331e8e27d75afebd))
* **role:** fix lint ([#188](https://github.com/aphp/Cohort360-Back-end/issues/188)) ([4aa6e70](https://github.com/aphp/Cohort360-Back-end/commit/4aa6e70df4c3c6aee48983d0d27571abc4b087b5))
* **roles:** add filtering and sorting to role users listing ([#203](https://github.com/aphp/Cohort360-Back-end/issues/203)) ([6ac52d1](https://github.com/aphp/Cohort360-Back-end/commit/6ac52d1adb411da55513fa6be3053a0860d93d78))


### Performance Improvements

* add Redis based cache ([#195](https://github.com/aphp/Cohort360-Back-end/issues/195)) ([5a97deb](https://github.com/aphp/Cohort360-Back-end/commit/5a97deb13ce2b8e44d0389d5cd0538f4a7158739))



## [3.12.4](https://github.com/aphp/Cohort360-Back-end/compare/3.12.3...3.12.4) (2023-05-12)


### Bug Fixes

* 3.12.4 squash migrations ([a68d503](https://github.com/aphp/Cohort360-Back-end/commit/a68d5035149083d098e042c8002b034353d0693c))
* adjust cohort and exports migrations ([9c9f986](https://github.com/aphp/Cohort360-Back-end/commit/9c9f9866d0d4e973a8134ab87856f96c180647bb))
* clean migrations ([c16aedf](https://github.com/aphp/Cohort360-Back-end/commit/c16aedfb5923231b67b184d87ef01906a1f0ad8f))
* force rm extra migration dir ([2b1dd37](https://github.com/aphp/Cohort360-Back-end/commit/2b1dd37fb7d91e84070fab8085ccf1f2b1343455))
* prepare squash script and isolate recent migrations ([#184](https://github.com/aphp/Cohort360-Back-end/issues/184)) ([67b48da](https://github.com/aphp/Cohort360-Back-end/commit/67b48daad0287dec83a56b95b1c0abe5b993668b))
* set default env vars values for tests ([87576c6](https://github.com/aphp/Cohort360-Back-end/commit/87576c64bb52d25a862488a81e9d18018d3c7ab6))
* squash migrations on starting container ([9f61182](https://github.com/aphp/Cohort360-Back-end/commit/9f61182f4fe6ddb35c674df174354cdfb53a38d2))


### Features

* alert users on accesses expiry ([#183](https://github.com/aphp/Cohort360-Back-end/issues/183)) ([c983a7c](https://github.com/aphp/Cohort360-Back-end/commit/c983a7c796620ac24def1d7ab60f3670737980f8))



## [3.12.3](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9-b...3.12.3) (2023-05-05)


### Bug Fixes

* up to v3.12.3 after hotfix prod ([ac1056e](https://github.com/aphp/Cohort360-Back-end/commit/ac1056e22d49b8ce40c9f7320b50990775f77142))



## [3.11.9-b](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9-a...3.11.9-b) (2023-05-05)


### Bug Fixes

* add inferior_levels and above_levels to perimeters serializers ([ca12460](https://github.com/aphp/Cohort360-Back-end/commit/ca124605d28e80839273bf014caee694ff80cee8))
* add provider_id on profile creation ([9e4dd91](https://github.com/aphp/Cohort360-Back-end/commit/9e4dd91ed874c5916b0a32d226af4ba8549b6431))
* do not create simple user on login ([4c10bf0](https://github.com/aphp/Cohort360-Back-end/commit/4c10bf091b608a21f1cfc35d2d8336c13aed757e))
* fix linter ([e34b2ba](https://github.com/aphp/Cohort360-Back-end/commit/e34b2bae0967ad170aa45fff457053bc5b0ec1da))
* return a JsonResponse in case of a JWT server error ([1a77001](https://github.com/aphp/Cohort360-Back-end/commit/1a7700139ee50aae9ac23a46c2cedc7e580e5795))
* test create dated measures and cancel running jobs ([ad5ea56](https://github.com/aphp/Cohort360-Back-end/commit/ad5ea56e1e4a144830d9b4b167db7774341fe1df))
* up to v3.11.9-b ([a8cdcf1](https://github.com/aphp/Cohort360-Back-end/commit/a8cdcf12015dbcb456a74886126cef365c73f923))


### Features

* **auth:** return a proper 401 http error on invalid login ([#179](https://github.com/aphp/Cohort360-Back-end/issues/179)) ([565126d](https://github.com/aphp/Cohort360-Back-end/commit/565126d205c562178addba556c9c0b075b22f7ad))



## [3.11.9-a](https://github.com/aphp/Cohort360-Back-end/compare/3.12.2...3.11.9-a) (2023-04-28)


### Bug Fixes

* add migration to patch perimeters_ids on RQSs ([1c1e14e](https://github.com/aphp/Cohort360-Back-end/commit/1c1e14eb15b5de4cdd9f2a8278e29dc3cb6d1c34))
* adjust migration dependency ([07c1108](https://github.com/aphp/Cohort360-Back-end/commit/07c1108f81390d54e8ef036f4a094433d77b4d53))
* clear cache on patch cohorts ([e8e3337](https://github.com/aphp/Cohort360-Back-end/commit/e8e3337ad4cc1ee605bc32634af4a7eff7558cc0))
* disable buggy cache ([ace7a34](https://github.com/aphp/Cohort360-Back-end/commit/ace7a34d327ccae0fe5fe876045ba61580c1b103))
* fhir OIDC auth to back ([86ad8f9](https://github.com/aphp/Cohort360-Back-end/commit/86ad8f98520f5b7662e545d9e38eed67a3c5c28d))
* Fhir OIDC auth to back ([f895234](https://github.com/aphp/Cohort360-Back-end/commit/f8952345e547ce09d0fb6b36a47fccedea792c61))
* fix flake8 errors ([f92f93f](https://github.com/aphp/Cohort360-Back-end/commit/f92f93fdcbac2fbd455d3180a5dd86bdaf8dd65e))
* flake8 error ([b3cbcb1](https://github.com/aphp/Cohort360-Back-end/commit/b3cbcb14053ae39f6b7e4196e7a6d2a2d1411d8b))
* improve response time ([#153](https://github.com/aphp/Cohort360-Back-end/issues/153)) ([c7c962f](https://github.com/aphp/Cohort360-Back-end/commit/c7c962f678a31a398c1653194a9c41e352561acc))
* log job response from CRB ([08fc046](https://github.com/aphp/Cohort360-Back-end/commit/08fc046fee5f187daf70d473aa67fb667edcbd14))
* notify creator not owner when export is done ([e137450](https://github.com/aphp/Cohort360-Back-end/commit/e1374507a6a5228f057176e05a25e98281f77f17))
* **perimeters:** add type and parent_id filter multi value refs:dev/c… ([#147](https://github.com/aphp/Cohort360-Back-end/issues/147)) ([dfb9e0c](https://github.com/aphp/Cohort360-Back-end/commit/dfb9e0ca411664248416ce9b6934b64d28a6c890))
* **perimeters:** change mapping, add above_list_ids ([#166](https://github.com/aphp/Cohort360-Back-end/issues/166)) ([471edc4](https://github.com/aphp/Cohort360-Back-end/commit/471edc44bff1c5518fdbb411265049f83d0f32cf))
* **perimeters:** change type mapping refs:dev/cohort360/gestion-de-pr… ([#150](https://github.com/aphp/Cohort360-Back-end/issues/150)) ([2e6481f](https://github.com/aphp/Cohort360-Back-end/commit/2e6481fe280df88efea38ed132b699d681de1360))
* rearrange cohort migrations files ([61997b6](https://github.com/aphp/Cohort360-Back-end/commit/61997b657957d1d4304a695ce663424c300a9fc1))
* remove cache for resources in cohort app ([78c6177](https://github.com/aphp/Cohort360-Back-end/commit/78c61774ee85394db55ed5a7b73ee500974b28e7))
* remove Django's parallel testing as not supported by gitlab runners ([c1122e5](https://github.com/aphp/Cohort360-Back-end/commit/c1122e5538302733a7e3d3d0d08e3778b19b8bf3))
* remove lof file rotation ([2fe52f3](https://github.com/aphp/Cohort360-Back-end/commit/2fe52f318b55730f5728a1c4b4198a7dbffdb271))
* remove unused import ([269792c](https://github.com/aphp/Cohort360-Back-end/commit/269792c39c8c519aa51062344dd2a1d994d9b6de))
* return proper response on export error ([f4f4b89](https://github.com/aphp/Cohort360-Back-end/commit/f4f4b89a189d44d0d7fb135efc645901319e041f))
* revert search users by provider_source_value ([ae403bf](https://github.com/aphp/Cohort360-Back-end/commit/ae403bfca2b1ab5d90c84d0e7bedb88048c82000))
* run parallel tests Django way ([b51aa62](https://github.com/aphp/Cohort360-Back-end/commit/b51aa62e977e7fe8d87d3063cb6b24919a694d27))
* search fields on exports list ([d2606f5](https://github.com/aphp/Cohort360-Back-end/commit/d2606f5f28cf857beccb0535eae5aee505ce5d61))
* temporarily remove cache for single DatedMeasure and RQS retrieve ([7899323](https://github.com/aphp/Cohort360-Back-end/commit/7899323089c0c03dc613dfed7a9668cd22056ac0))
* temporarily remove cache for single DatedMeasure retrieve ([12ac462](https://github.com/aphp/Cohort360-Back-end/commit/12ac462c251472ecf218d2b21d454912f64f841e))
* temporarily remove cache for single DatedMeasure retrieve ([4e48817](https://github.com/aphp/Cohort360-Back-end/commit/4e4881766599a470be56ae19bb7d45b335809bcc))
* update influxdb token env var ([588924e](https://github.com/aphp/Cohort360-Back-end/commit/588924ead464621e88c89711cb68036282a8b96e))
* update page_size to 20 in tests ([685e793](https://github.com/aphp/Cohort360-Back-end/commit/685e7930b5969898d493389b03188f0a14de16ff))


### Features

* make infra api calls async ([#167](https://github.com/aphp/Cohort360-Back-end/issues/167)) ([ee27843](https://github.com/aphp/Cohort360-Back-end/commit/ee278436f5e3446077baf6a228049afad8873e66))
* run parallel tests gitlab ci ([#143](https://github.com/aphp/Cohort360-Back-end/issues/143)) ([b518a32](https://github.com/aphp/Cohort360-Back-end/commit/b518a325415e1e5c191d837fe41854b5ee872cc7))


### Performance Improvements

* add cache to improve response time ([#160](https://github.com/aphp/Cohort360-Back-end/issues/160)) ([2b38d25](https://github.com/aphp/Cohort360-Back-end/commit/2b38d257d59383cf34bbe8cfc5a2b952a154bb77))
* add InfluxDB middleware to collect metrics ([#148](https://github.com/aphp/Cohort360-Back-end/issues/148)) ([6c8a782](https://github.com/aphp/Cohort360-Back-end/commit/6c8a7823c39272c2e0ab91b2ca3314e288785bcf))
* cache exports requests and fix tests ([#154](https://github.com/aphp/Cohort360-Back-end/issues/154)) ([01f0c5b](https://github.com/aphp/Cohort360-Back-end/commit/01f0c5be037e055f6a9a9678ff1cf336f9d3cfc8))
* improve response time ([#162](https://github.com/aphp/Cohort360-Back-end/issues/162)) ([88fd9dd](https://github.com/aphp/Cohort360-Back-end/commit/88fd9dd314b223260d82245241d23a02035dea10))



## [3.12.5](https://github.com/aphp/Cohort360-Back-end/compare/3.12.4...3.12.5) (2023-06-07)


### Bug Fixes

* 3.12.5 increase Nginx client_max_body_size param ([#194](https://github.com/aphp/Cohort360-Back-end/issues/194)) ([23c300b](https://github.com/aphp/Cohort360-Back-end/commit/23c300b5f3483fa955291fb198f40b2855f721e2))
* up to v3.12.3 after hotfix prod ([b210e77](https://github.com/aphp/Cohort360-Back-end/commit/b210e7790213a6db430ac6e1f81193e244117098))



## [3.12.4](https://github.com/aphp/Cohort360-Back-end/compare/3.12.3...3.12.4) (2023-05-12)


### Bug Fixes

* 3.12.4 squash migrations ([a68d503](https://github.com/aphp/Cohort360-Back-end/commit/a68d5035149083d098e042c8002b034353d0693c))
* adjust cohort and exports migrations ([9c9f986](https://github.com/aphp/Cohort360-Back-end/commit/9c9f9866d0d4e973a8134ab87856f96c180647bb))
* squash migrations on starting container ([9f61182](https://github.com/aphp/Cohort360-Back-end/commit/9f61182f4fe6ddb35c674df174354cdfb53a38d2))



## [3.12.3](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9-b...3.12.3) (2023-05-05)


### Bug Fixes

* up to v3.12.3 after hotfix prod ([ac1056e](https://github.com/aphp/Cohort360-Back-end/commit/ac1056e22d49b8ce40c9f7320b50990775f77142))



## [3.12.2](https://github.com/aphp/Cohort360-Back-end/compare/3.12.1...3.12.2) (2023-04-28)


### Bug Fixes

* notify creator not owner when export is done ([#176](https://github.com/aphp/Cohort360-Back-end/issues/176)) ([5ea8f31](https://github.com/aphp/Cohort360-Back-end/commit/5ea8f312ecebb3c0ccdc8da0511a78c5aec04136))
* notify creator not owner when export is done ([#177](https://github.com/aphp/Cohort360-Back-end/issues/177)) ([e4140e1](https://github.com/aphp/Cohort360-Back-end/commit/e4140e1147a865d60435908e3ed423c091973208))
* remove unused import ([e51b6e7](https://github.com/aphp/Cohort360-Back-end/commit/e51b6e714c045267b47882554bb652931abc8a96))



## [3.12.1](https://github.com/aphp/Cohort360-Back-end/compare/3.12.0...3.12.1) (2023-04-26)


### Bug Fixes

* disable buggy cache ([6a0116b](https://github.com/aphp/Cohort360-Back-end/commit/6a0116bce9fd749c990d57f958152a5da86a7bce))
* remove buggy cache ([#174](https://github.com/aphp/Cohort360-Back-end/issues/174)) ([193e21b](https://github.com/aphp/Cohort360-Back-end/commit/193e21b4b8d0d5a983be8938622db7e5bb6546b7))



# [3.12.0](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9...3.12.0) (2023-04-03)


### Bug Fixes

* flake8 error ([2333009](https://github.com/aphp/Cohort360-Back-end/commit/23330096adee2e52ff69f057c2ff6328f2499eea))
* remove cache for resources in cohort app ([#163](https://github.com/aphp/Cohort360-Back-end/issues/163)) ([d9ce471](https://github.com/aphp/Cohort360-Back-end/commit/d9ce471a1c1a5ef846f6d90a1eb6f59611c4272f))



## [3.11.9-b](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9-a...3.11.9-b) (2023-05-05)


### Bug Fixes

* add provider_id on profile creation ([9e4dd91](https://github.com/aphp/Cohort360-Back-end/commit/9e4dd91ed874c5916b0a32d226af4ba8549b6431))
* do not create simple user on login ([4c10bf0](https://github.com/aphp/Cohort360-Back-end/commit/4c10bf091b608a21f1cfc35d2d8336c13aed757e))
* up to v3.11.9-b ([a8cdcf1](https://github.com/aphp/Cohort360-Back-end/commit/a8cdcf12015dbcb456a74886126cef365c73f923))



## [3.11.9-a](https://github.com/aphp/Cohort360-Back-end/compare/3.12.2...3.11.9-a) (2023-04-28)


### Bug Fixes

* notify creator not owner when export is done ([e137450](https://github.com/aphp/Cohort360-Back-end/commit/e1374507a6a5228f057176e05a25e98281f77f17))



## [3.12.2](https://github.com/aphp/Cohort360-Back-end/compare/3.12.1...3.12.2) (2023-04-28)


### Bug Fixes

* notify creator not owner when export is done ([#176](https://github.com/aphp/Cohort360-Back-end/issues/176)) ([5ea8f31](https://github.com/aphp/Cohort360-Back-end/commit/5ea8f312ecebb3c0ccdc8da0511a78c5aec04136))
* notify creator not owner when export is done ([#177](https://github.com/aphp/Cohort360-Back-end/issues/177)) ([e4140e1](https://github.com/aphp/Cohort360-Back-end/commit/e4140e1147a865d60435908e3ed423c091973208))
* remove unused import ([e51b6e7](https://github.com/aphp/Cohort360-Back-end/commit/e51b6e714c045267b47882554bb652931abc8a96))



## [3.12.1](https://github.com/aphp/Cohort360-Back-end/compare/3.12.0...3.12.1) (2023-04-26)


### Bug Fixes

* disable buggy cache ([6a0116b](https://github.com/aphp/Cohort360-Back-end/commit/6a0116bce9fd749c990d57f958152a5da86a7bce))
* remove buggy cache ([#174](https://github.com/aphp/Cohort360-Back-end/issues/174)) ([193e21b](https://github.com/aphp/Cohort360-Back-end/commit/193e21b4b8d0d5a983be8938622db7e5bb6546b7))



# [3.12.0](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9...3.12.0) (2023-04-03)


### Bug Fixes

* flake8 error ([2333009](https://github.com/aphp/Cohort360-Back-end/commit/23330096adee2e52ff69f057c2ff6328f2499eea))
* remove cache for resources in cohort app ([#163](https://github.com/aphp/Cohort360-Back-end/issues/163)) ([d9ce471](https://github.com/aphp/Cohort360-Back-end/commit/d9ce471a1c1a5ef846f6d90a1eb6f59611c4272f))



## [3.11.9](https://github.com/aphp/Cohort360-Back-end/compare/3.11.8...3.11.9) (2023-03-31)



## [3.11.8](https://github.com/aphp/Cohort360-Back-end/compare/3.11.7...3.11.8) (2023-03-31)


### Bug Fixes

* fhir OIDC auth to back ([#157](https://github.com/aphp/Cohort360-Back-end/issues/157)) ([2d7c5d2](https://github.com/aphp/Cohort360-Back-end/commit/2d7c5d26ad7582da2c75aa6551d64b6c6fe891b5))



## [3.11.7](https://github.com/aphp/Cohort360-Back-end/compare/3.11.6...3.11.7) (2023-03-27)


### Bug Fixes

* return proper response on export error ([#155](https://github.com/aphp/Cohort360-Back-end/issues/155)) ([5386562](https://github.com/aphp/Cohort360-Back-end/commit/538656252875971ff6af20c060ae4197d40869be))



## [3.11.6](https://github.com/aphp/Cohort360-Back-end/compare/3.11.5...3.11.6) (2023-03-17)


### Bug Fixes

* hotfix v3.11.6 for cohort migrations order ([#152](https://github.com/aphp/Cohort360-Back-end/issues/152)) ([8ac561f](https://github.com/aphp/Cohort360-Back-end/commit/8ac561ffdb1b4e35ae5de78d3a397c78b9518a08))



## [3.11.5](https://github.com/aphp/Cohort360-Back-end/compare/3.11.4...3.11.5) (2023-03-15)


### Bug Fixes

* **perimeters:** add type and parent_id filter multi value refs:dev/c… ([#149](https://github.com/aphp/Cohort360-Back-end/issues/149)) ([8b2a849](https://github.com/aphp/Cohort360-Back-end/commit/8b2a8490538eb861c5494c814e40bf5521870e45))



## [3.11.4](https://github.com/aphp/Cohort360-Back-end/compare/3.11.3...3.11.4) (2023-03-14)


### Bug Fixes

* hotfix v3.11.4 ([85ad05e](https://github.com/aphp/Cohort360-Back-end/commit/85ad05e806c836f8bb7e3667d397015fd3f3d3b3))
* remove log file rotation ([#146](https://github.com/aphp/Cohort360-Back-end/issues/146)) ([1b3e6af](https://github.com/aphp/Cohort360-Back-end/commit/1b3e6af2e854c761f3bcbafe470f59e85d9aeff7))



## [3.11.3](https://github.com/aphp/Cohort360-Back-end/compare/3.11.2...3.11.3) (2023-03-06)



## [3.11.1](https://github.com/aphp/Cohort360-Back-end/compare/3.11.0...3.11.1) (2023-03-01)



## [3.10.3](https://github.com/aphp/Cohort360-Back-end/compare/3.10.2...3.10.3) (2023-02-09)



## [3.9.3](https://github.com/aphp/Cohort360-Back-end/compare/3.9.2...3.9.3) (2023-01-10)



# [3.9.0](https://github.com/aphp/Cohort360-Back-end/compare/3.8.5...3.9.0) (2023-01-05)



## [3.8.5](https://github.com/aphp/Cohort360-Back-end/compare/3.8.4...3.8.5) (2022-12-21)



## [3.8.4](https://github.com/aphp/Cohort360-Back-end/compare/3.8.3...3.8.4) (2022-12-21)


### Reverts

* Revert "Launch celery in detach mode" ([331b0f6](https://github.com/aphp/Cohort360-Back-end/commit/331b0f6fd5982d87566ee3dd332d9228c12e88ab))



## [3.8.3](https://github.com/aphp/Cohort360-Back-end/compare/3.8.2...3.8.3) (2022-12-15)



## [3.8.2](https://github.com/aphp/Cohort360-Back-end/compare/3.8.1...3.8.2) (2022-12-08)



# [3.8.0](https://github.com/aphp/Cohort360-Back-end/compare/3.7.5...3.8.0) (2022-12-05)



## [3.7.5](https://github.com/aphp/Cohort360-Back-end/compare/3.7.4...3.7.5) (2022-12-02)



## [3.7.4](https://github.com/aphp/Cohort360-Back-end/compare/3.7.3...3.7.4) (2022-11-29)


### Reverts

* Revert "HOT FIX name perimeter table in migration table" ([f1d83b8](https://github.com/aphp/Cohort360-Back-end/commit/f1d83b85e12e85ceae48577557b8375d3910096e))



## [3.7.3](https://github.com/aphp/Cohort360-Back-end/compare/3.7.2...3.7.3) (2022-11-24)



## [3.7.2](https://github.com/aphp/Cohort360-Back-end/compare/3.7.1...3.7.2) (2022-11-23)


### Bug Fixes

* email formatting ([83e7b88](https://github.com/aphp/Cohort360-Back-end/commit/83e7b889fcb9a3f3918d816d8825630b0557f4fc))
* read env variables directly from os.environ instead of loading a non-existing .env file in accesses app. ([e831f21](https://github.com/aphp/Cohort360-Back-end/commit/e831f2133f5b8816ee19679544205c7566f4dbd6))


### Reverts

* Revert "Rollback filters in /cohorts" ([c734e78](https://github.com/aphp/Cohort360-Back-end/commit/c734e78fdd05ee9e6ca6936c54479539633ca73a))
* Revert "Rollback filters in /cohorts" ([532c3d9](https://github.com/aphp/Cohort360-Back-end/commit/532c3d9afb94b479597d8e7f19ded0e4de8aaf5b))
* Revert "Rollback filters in /cohorts" ([abe993d](https://github.com/aphp/Cohort360-Back-end/commit/abe993d17cd7dc99ab25b8d10bb2c34abd874d61))
* Revert "[3.7.0-SNAPSHOT] removed CodeQL analysis as it's no longer available for private repo" ([1818329](https://github.com/aphp/Cohort360-Back-end/commit/1818329be01a34688b22c663ac7484cc4c34f7eb))



## [3.6.5](https://github.com/aphp/Cohort360-Back-end/compare/3.6.4...3.6.5) (2022-09-05)



## [3.6.4](https://github.com/aphp/Cohort360-Back-end/compare/3.6.3...3.6.4) (2022-08-29)



## [3.6.3](https://github.com/aphp/Cohort360-Back-end/compare/3.6.2...3.6.3) (2022-08-23)



## [3.6.2](https://github.com/aphp/Cohort360-Back-end/compare/3.6.1...3.6.2) (2022-08-23)



## [3.6.1](https://github.com/aphp/Cohort360-Back-end/compare/3.6.0...3.6.1) (2022-08-22)



# [3.6.0](https://github.com/aphp/Cohort360-Back-end/compare/3.5.3...3.6.0) (2022-08-22)



## [3.5.3](https://github.com/aphp/Cohort360-Back-end/compare/3.5.2...3.5.3) (2022-08-10)



## [3.5.2](https://github.com/aphp/Cohort360-Back-end/compare/3.5.1...3.5.2) (2022-08-08)



## [3.5.1](https://github.com/aphp/Cohort360-Back-end/compare/3.5.0...3.5.1) (2022-08-08)



# 3.5.0 (2022-08-02)




# Cohort Scripts

This directory contains patch scripts for updating query snapshots and filters across different versions of the cohort system. These scripts handle database migrations for FHIR query structures and ensure compatibility between versions.

## Overview

The scripts follow a versioned approach where each script handles updating from one or more previous versions to a new version. All scripts use the `QueryRequestUpdater` class from `query_request_updater.py` to perform systematic updates to:

- Resource type mappings
- Filter name mappings  
- Filter value transformations
- Static required filters
- Version tracking

## Script Structure

Each patch script follows this pattern:

```python
from cohort.scripts.patch_requests_v{prev_version} import NEW_VERSION as PREV_VERSION
from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, QueryRequestUpdater

NEW_VERSION = "v1.x.x"

# Configuration dictionaries
FILTER_MAPPING = {}
FILTER_NAME_TO_SKIP = {}
FILTER_VALUE_MAPPING = {}
STATIC_REQUIRED_FILTERS = {}
RESOURCE_NAME_MAPPING = {}

# Create updater instance
updater_v{version} = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING,
)
```

## Creating a New Patch Script

To create a new patch script (e.g., `patch_requests_v162.py`):

1. **Create the file**: Follow the naming convention `patch_requests_v{version}.py`

2. **Set up imports and version**:
   ```python
   from cohort.scripts.patch_requests_v161 import NEW_VERSION as PREV_VERSION
   from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, QueryRequestUpdater
   
   NEW_VERSION = "v1.6.2"
   ```

3. **Configure mapping dictionaries**:
   - `FILTER_MAPPING`: Maps old filter names to new ones per resource type
   - `FILTER_NAME_TO_SKIP`: Filters to remove during update
   - `FILTER_VALUE_MAPPING`: Transform filter values (supports functions)
   - `STATIC_REQUIRED_FILTERS`: Add required filters to resources
   - `RESOURCE_NAME_MAPPING`: Map old resource names to new ones

4. **Example configurations**:
   ```python
   FILTER_MAPPING = {
       "Encounter": {
           "old-filter-name": "new-filter-name"
       },
       RESOURCE_DEFAULT: {
           "global-old-name": "global-new-name"
       }
   }
   
   FILTER_VALUE_MAPPING = {
       "MedicationRequest": {
           "medication": {
               "old-code|value": "new-code|value",
               "__MATCH_ALL_VALUES__": lambda x: transform_function(x)
           }
       }
   }
   ```

5. **Create the updater instance**:
   ```python
   updater_v162 = QueryRequestUpdater(
       version_name=NEW_VERSION,
       previous_version_name=[PREV_VERSION],
       filter_mapping=FILTER_MAPPING,
       filter_names_to_skip=FILTER_NAME_TO_SKIP,
       filter_values_mapping=FILTER_VALUE_MAPPING,
       static_required_filters=STATIC_REQUIRED_FILTERS,
       resource_name_mapping=RESOURCE_NAME_MAPPING,
   )
   ```

## Running Patch Scripts

### Development Environment
```bash
python manage.py shell
```

```python
from cohort.scripts.patch_requests_v161 import updater_v161
updater_v161.update_old_query_snapshots(
    dry_run=True,    # Set to False to apply changes
    debug=True,      # Enable debug logging
    with_filters=True  # Also update FhirFilter objects
)
```

### Production Environment
1. Connect to a running pod:
   ```bash
   kubectl exec -it <pod_name> -- bash
   ```

2. Activate virtual environment:
   ```bash
   source .venv/bin/activate
   ```

3. Run Django shell:
   ```bash
   python manage.py shell
   ```

4. Execute the patch:
   ```python
   from cohort.scripts.patch_requests_v161 import updater_v161
   updater_v161.update_old_query_snapshots(
       dry_run=False,
       debug=True,
       with_filters=True,
   )
   ```

## Parameters

- `dry_run` (bool): When `True`, shows what would be changed without applying changes
- `debug` (bool): Enables verbose logging and saves debug files
- `with_filters` (bool): Also updates standalone FhirFilter objects

## Best Practices

1. **Always test with dry_run=True first** to validate changes
2. **Use debug=True** to get detailed logs and debug files
3. **Version incrementally** - each script should handle one version bump
4. **Handle multiple previous versions** when consolidating updates
5. **Test transformations thoroughly** before production deployment
6. **Monitor logs** during execution for errors or unexpected behavior

## Current Scripts

- `patch_requests_v130.py` through `patch_requests_v161.py`: Version-specific update scripts
- `query_request_updater.py`: Core updater class and utilities

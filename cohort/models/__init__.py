# from .folder import Folder
# from .request import Request
# from .request_query_snapshot import RequestQuerySnapshot
# from .dated_measure import DatedMeasure
# from .cohort_result import CohortResult

COHORT_TYPE_CHOICES = [("IMPORT_I2B2", "Previous cohorts imported from i2b2.",),
                       ("MY_ORGANIZATIONS", "Organizations in which I work (care sites "
                                            "with pseudo-anonymised reading rights).",),
                       ("MY_PATIENTS", "Patients that passed by all my organizations "
                                       "(care sites with nominative reading rights)."),
                       ("MY_COHORTS", "Cohorts I created in Cohort360")]

I2B2_COHORT_TYPE = COHORT_TYPE_CHOICES[0][0]
MY_ORGANISATIONS_COHORT_TYPE = COHORT_TYPE_CHOICES[1][0]
MY_PATIENTS_COHORT_TYPE = COHORT_TYPE_CHOICES[2][0]
MY_COHORTS_COHORT_TYPE = COHORT_TYPE_CHOICES[3][0]

REQUEST_DATA_TYPE_CHOICES = [('PATIENT', 'FHIR Patient'),
                             ('ENCOUNTER', 'FHIR Encounter')]
PATIENT_REQUEST_TYPE = REQUEST_DATA_TYPE_CHOICES[0][0]

SNAPSHOT_DM_MODE = "Snapshot"
GLOBAL_DM_MODE = "Global"
DATED_MEASURE_MODE_CHOICES = [(SNAPSHOT_DM_MODE, SNAPSHOT_DM_MODE),
                              (GLOBAL_DM_MODE, GLOBAL_DM_MODE)]

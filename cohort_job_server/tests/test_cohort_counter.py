from django.test import TestCase

from cohort_job_server.cohort_counter import CohortCounter


class CohortCounterTest(TestCase):

    def setUp(self):
        super().setUp()
        self.cohort_counter = CohortCounter()

    def test_launch_dated_measure_count(self):
        ...
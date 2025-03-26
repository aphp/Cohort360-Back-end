from io import StringIO

from django.core.management import call_command

from accesses.models import Perimeter, Role
from admin_cohort.management.commands import load_initial_data
from admin_cohort.models import User
from admin_cohort.tests.tests_tools import TestCaseWithDBs


class LoadInitialDataCommandTest(TestCaseWithDBs):

    def test_load_initial_data_command(self):
        out = StringIO()
        file_path = '.setup/perimeters.example.csv'
        call_command(load_initial_data.Command(),
                     perimeters_conf=file_path,
                     stdout=out)
        perimeters = Perimeter.objects.all()
        user = User.objects.filter(username__icontains='admin')
        admin_role = Role.objects.filter(right_full_admin=True)
        self.assertIsNotNone(perimeters)
        self.assertIsNotNone(user)
        self.assertIsNotNone(admin_role)
        self.assertIn('Successfully added user', out.getvalue())

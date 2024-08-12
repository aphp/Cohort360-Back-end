import csv
import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accesses.models import Perimeter, Profile, Role, Access
from admin_cohort.models import User

env = os.environ

ADMIN_USERNAME = env.get('ADMIN_USERNAME', 'admin')
ADMIN_FIRSTNAME = env.get('ADMIN_FIRSTNAME', '')
ADMIN_LASTNAME = env.get('ADMIN_LASTNAME', '')
ADMIN_EMAIL = env.get('ADMIN_EMAIL', '')
SJS_USERNAME = env.get('SJS_USERNAME', 'SPARK_JOB_SERVER')


class Command(BaseCommand):
    help = 'Load perimeters data from a CSV file into the DB'

    def add_arguments(self, parser):
        parser.add_argument('--perimeters-conf', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        self.load_perimeters(csv_file_path=options['perimeters_conf'])
        self.create_cohort_requester_profile()
        admin_profile = self.create_admin_profile()
        self.assign_admin_role(profile=admin_profile)
        self.stdout.write(self.style.SUCCESS(f"Successfully added user '{ADMIN_USERNAME}' with Full Admin role"))

    def load_perimeters(self, csv_file_path: str) -> None:
        with open(csv_file_path, 'r') as csv_file:
            reader = csv.DictReader(csv_file, delimiter=";")
            count = 0
            for row in reader:
                Perimeter.objects.create(**row)
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} perimeters'))

    @staticmethod
    def check_for_existing_user(username) -> User | bool:
        existing_user = User.objects.filter(username=username).first()
        return existing_user or False

    def create_profile(self, username, firstname, lastname, email) -> Profile:
        existing_user = self.check_for_existing_user(username)
        if existing_user:
            self.stdout.write(self.style.WARNING(f'Found an old user {username} in DB, proceed with it'))
            return existing_user.profiles.first()

        user_data = dict(firstname=firstname,
                         lastname=lastname,
                         email=email)
        user = User.objects.create(**user_data, username=username, provider_id=username)
        profile = Profile.objects.create(user_id=user.username, is_active=True)
        return profile

    def create_admin_profile(self) -> Profile:
        return self.create_profile(ADMIN_USERNAME, ADMIN_FIRSTNAME, ADMIN_LASTNAME, ADMIN_EMAIL)

    def create_cohort_requester_profile(self) -> Profile:
        return self.create_profile(SJS_USERNAME, 'cohort', 'requester', 'cohort.requester@cohort360.org')

    @staticmethod
    def assign_admin_role(profile: Profile) -> None:
        admin_role = Role.objects.create(name="Full Admin")
        for field in [f.name for f in Role._meta.fields if f.name.startswith("right_")]:
            setattr(admin_role, field, True)
            admin_role.save()

        try:
            root_perimeter = Perimeter.objects.get(parent__isnull=True)
        except (Perimeter.DoesNotExist, Perimeter.MultipleObjectsReturned):
            raise ValueError("CSV file configuration error: ensure you have a single root perimeter")
        else:
            Access.objects.create(profile=profile,
                                  role=admin_role,
                                  perimeter=root_perimeter,
                                  start_datetime=timezone.now(),
                                  end_datetime=timezone.now() + timedelta(days=365))

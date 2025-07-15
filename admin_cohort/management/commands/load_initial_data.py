import csv
import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accesses.models import Perimeter, Profile, Role, Access
from admin_cohort.models import User
from admin_cohort.services.users import users_service

env = os.environ

ADMIN_USERNAME = env.get('ADMIN_USERNAME', 'admin')
ADMIN_FIRSTNAME = env.get('ADMIN_FIRSTNAME', 'Admin')
ADMIN_LASTNAME = env.get('ADMIN_LASTNAME', 'ADMIN')
ADMIN_EMAIL = env.get('ADMIN_EMAIL', 'admin@backend.fr')
ADMIN_PASSWORD = env.get('ADMIN_PASSWORD', 'admin')
QUERY_EXECUTOR_USERNAME = env.get('QUERY_EXECUTOR_USERNAME', 'QUERY_EXECUTOR')
QUERY_EXECUTOR_PASSWORD = env.get('QUERY_EXECUTOR_PASSWORD', '1234')


class Command(BaseCommand):
    help = 'Load perimeters data from a CSV file into the DB'

    def add_arguments(self, parser):
        parser.add_argument('--perimeters-conf', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        self.load_perimeters(csv_file_path=options['perimeters_conf'])
        self.setup_admin_user_account()
        self.setup_query_executor_user_account()
        self.stdout.write(self.style.SUCCESS(f"Successfully added user '{ADMIN_USERNAME}' with 'Full Admin' role"))

    def load_perimeters(self, csv_file_path: str) -> None:
        with open(csv_file_path, 'r') as csv_file:
            reader = csv.DictReader(csv_file, delimiter=";")
            count = 0
            for row in reader:
                Perimeter.objects.create(**row)
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} perimeters'))

    def create_profile(self, username, firstname, lastname, email, password) -> Profile:
        existing_user = User.objects.filter(username=username).first()
        if existing_user is not None:
            self.stdout.write(self.style.WARNING(f'Found an old user {username} in DB, proceed with it'))
            return existing_user.profiles.first()

        user = User.objects.create(username=username,
                                   firstname=firstname,
                                   lastname=lastname,
                                   email=email,
                                   password=users_service.hash_password(password))
        profile = Profile.objects.create(user_id=user.username, is_active=True)
        return profile

    def setup_query_executor_user_account(self) -> None:
        _ = self.create_profile(username=QUERY_EXECUTOR_USERNAME,
                                firstname='Query',
                                lastname='EXECUTOR',
                                email='query_executor@example.org',
                                password=QUERY_EXECUTOR_PASSWORD
                                )

    def setup_admin_user_account(self) -> None:
        profile = self.create_profile(username=ADMIN_USERNAME,
                                      firstname=ADMIN_FIRSTNAME,
                                      lastname=ADMIN_LASTNAME,
                                      email=ADMIN_EMAIL,
                                      password=ADMIN_PASSWORD
                                      )
        rights = {f.name: True for f in Role._meta.fields if f.name.startswith("right_")}
        admin_role = Role.objects.create(name="Full Admin", **rights)

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

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import hashlib

from admin_cohort.models import User
from accesses.models import Role, Perimeter, Access, Profile

DEFAULT_PASSWORD = "TEST"
DEFAULT_USERNAME = "420123456"
PERIMETER_ID_AP = 8312002244


class Command(BaseCommand):
    help = "Generate admin user for local development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            default=DEFAULT_USERNAME,
            help="Username of the admin user to create/update",
        )
        parser.add_argument(
            "--password",
            type=str,
            default=DEFAULT_PASSWORD,
            help="Password of the admin user to create/update",
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        self.stdout.write(f"--- Generating admin user {username} ---")

        # Hash password
        hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()

        # 1. User
        user, created = User.objects.update_or_create(
            username=username,
            defaults={
                "firstname": "John",
                "lastname": "DOE",
                "email": (
                    f"john.doe.{username}@aphp.fr"
                    if username != DEFAULT_USERNAME
                    else "john.doe@aphp.fr"
                ),
                "password": hashed_password,
            },
        )
        self.stdout.write(f"User {username} {'created' if created else 'updated'}.")

        # 2. Role
        role_id = 123456
        role_name = "LOCAL TESTER ROLE"

        role_data = {
            "name": role_name,
            "right_full_admin": True,
            "right_manage_users": True,
            "right_manage_datalabs": True,
            "right_read_datalabs": True,
            "right_export_csv_xlsx_nominative": True,
            "right_export_jupyter_nominative": True,
            "right_export_jupyter_pseudonymized": True,
            "right_manage_admin_accesses_same_level": True,
            "right_manage_admin_accesses_inferior_levels": True,
            "right_manage_data_accesses_same_level": True,
            "right_manage_data_accesses_inferior_levels": True,
            "right_read_patient_nominative": True,
            "right_read_patient_pseudonymized": True,
            "right_search_patients_by_ipp": True,
            "right_search_patients_unlimited": True,
            "right_search_opposed_patients": True,
        }

        role = Role.objects.filter(id=role_id).first()

        if role:
            self.stdout.write(f"Role with ID {role_id} found. Updating it...")
            for key, value in role_data.items():
                setattr(role, key, value)
            role.save()
            created = False
        else:
            role = Role.objects.filter(name=role_name).first()
            if role:
                self.stdout.write(
                    f"Role with name '{role_name}' found (ID {role.id}). Updating it..."
                )
                for key, value in role_data.items():
                    setattr(role, key, value)
                role.save()
                created = False
            else:
                self.stdout.write(
                    f"Creating new role with ID {role_id} and name '{role_name}'..."
                )
                role = Role.objects.create(id=role_id, **role_data)
                created = True

        self.stdout.write(
            f"Role {role.id} ({role.name}) {'created' if created else 'updated'}."
        )

        # 3. Perimeter
        try:
            perimeter = Perimeter.objects.get(id=PERIMETER_ID_AP)
            self.stdout.write(
                f"Perimeter {PERIMETER_ID_AP} found: {perimeter.name}"
            )
        except Perimeter.DoesNotExist:
            self.stdout.write(
                f"Perimeter {PERIMETER_ID_AP} NOT found. Creating it..."
            )
            perimeter = Perimeter.objects.create(
                id=PERIMETER_ID_AP,
                local_id=f"LOCAL_{PERIMETER_ID_AP}",
                name="Top Perimeter",
                level=0,
            )
            self.stdout.write(f"Perimeter {PERIMETER_ID_AP} created.")

        # 4. Profile
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={"is_active": True},
        )
        if created:
            self.stdout.write(f"Profile for user {username} created.")

        # 5. Access
        now = timezone.now()
        access, created = Access.objects.update_or_create(
            profile=profile,
            perimeter=perimeter,
            defaults={
                "role": role,
                "start_datetime": now - timedelta(days=1),
                "end_datetime": now + timedelta(weeks=52 * 100),
                "source": "Manual",
            },
        )

        if created:
            self.stdout.write(
                f"Access created for user {username} on perimeter {PERIMETER_ID_AP} with role {role.id}."
            )
        else:
            access.role = role
            access.start_datetime = now - timedelta(days=1)
            access.end_datetime = now + timedelta(weeks=52 * 100)
            access.save()

            self.stdout.write(
                f"Access updated for user {username} on perimeter {PERIMETER_ID_AP} with role {role.id}."
            )

        self.stdout.write(self.style.SUCCESS("✔ User generation completed successfully"))
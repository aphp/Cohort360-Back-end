from django.core.management.base import BaseCommand
from admin_cohort.models import User
from accesses.models import Profile, Access, Role, Perimeter
from django.utils import timezone
from datetime import timedelta

PERIMETER_ID = "1234567890"


class Command(BaseCommand):
    help = "Génère des utilisateurs fictifs avec des accès associés"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=12, help="Nombre d'utilisateurs à générer (par défaut 12)")
        parser.add_argument("--perimeter_id", type=str, default=PERIMETER_ID, help="ID du périmètre à associer")
        parser.add_argument("--role_id", type=int, default=4, help="ID du rôle à associer")

    def handle(self, *args, **options):
        count = options["count"]
        perimeter_id = options["perimeter_id"]
        role_id = options["role_id"]

        try:
            perimeter = Perimeter.objects.get(id=perimeter_id)
        except Perimeter.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Périmètre avec l'ID {perimeter_id} introuvable."))
            return

        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Rôle avec l'ID {role_id} introuvable."))
            return

        for i in range(count):
            username = str(10000000 + i)  # Similaire à l'exemple 12345678
            while User.objects.filter(username=username).exists():
                username = str(int(username) + 100)  # Pour éviter les collisions si déjà lancé

            firstname = "John" if i % 2 == 0 else "Jane"
            lastname = f"DOE_{i}"

            user = User.objects.create(username=username, firstname=firstname, lastname=lastname, email=f"{username}@example.com")

            profile = Profile.objects.create(user=user, source="Manual", is_active=True)

            # Dates pour Access (on peut les rendre invalides comme dans l'exemple si besoin)
            # L'exemple montre des dates passées, ce qui rend is_valid = False
            start_date = timezone.now() - timedelta(days=20)
            end_date = timezone.now() + timedelta(days=1000)

            Access.objects.create(profile=profile, role=role, perimeter=perimeter, start_datetime=start_date, end_datetime=end_date, source="Manual")

            self.stdout.write(self.style.SUCCESS(f"Utilisateur {username} créé avec succès."))

        self.stdout.write(self.style.SUCCESS(f"{count} utilisateurs fictifs ont été générés."))

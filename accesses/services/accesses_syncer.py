import logging
from dataclasses import dataclass
from datetime import datetime
from itertools import batched

from django.conf import settings
from django.utils import timezone
from fhirpy import SyncFHIRClient

from accesses.apps import AccessConfig
from accesses.migrations.data.orbis_roles_map import roles_map
from accesses.models import Role, Profile, Perimeter, Access
from admin_cohort.emails import EmailNotification
from admin_cohort.models import User
from admin_cohort.services.auth import jwt_auth_service


_logger = logging.getLogger("info")

_, ORBIS = settings.ACCESS_SOURCES


@dataclass
class FhirPractitioner:
    username: str
    firstname: str
    lastname: str


@dataclass
class FhirPractitionerRole:
    id: str
    active: bool
    practitioner_id: str
    perimeter_id: int
    role_name: str
    start_datetime: datetime
    end_datetime: datetime


class AccessesSynchronizer:

    def __init__(self):
        token = jwt_auth_service.generate_system_token()
        self.fhir_client = SyncFHIRClient(url=AccessConfig.FHIR_URL,
                                          authorization=f"Bearer {token}")

    @staticmethod
    def log(message: str):
        _logger.info(f"[ORBIS sync] {message}")

    def sync_orbis_resources(self):
        # self.sync_profiles()
        self.sync_accesses()


    @staticmethod
    def get_mapped_role(role_name) -> Role:
        mapped_role_name = [k for k in roles_map if role_name in roles_map[k]]
        return Role.objects.filter(name__in=mapped_role_name).first()


    def sync_profiles(self):
        """
        Using the Practitioner resource cf. https://hl7.org/fhir/R4/practitioner.html
        For active Practitioners, if the corresponding user exists, create a Profile for it with source="ORBIS" if it does not have any.
        For later syncing, inactive Practitioners will have their corresponding profiles deactivated.
        @return: None
        """
        practitioner_res = self.fhir_client.resources("Practitioner")

        for p in practitioner_res.fetch_all():
            if p.active:
                practitioner = FhirPractitioner(username=p.identifier[0].value,
                                                firstname=p.name[0].given[0],
                                                lastname=p.name[0].family
                                                )
                user = User.objects.filter(username=practitioner.username).first()
                if user or not user.profiles.filter(source=ORBIS, is_active=True).exists():
                    Profile.objects.create(user=user, source=ORBIS, is_active=True)
            else:
                linked_profiles = Profile.objects.filter(user_id=p.identifier[0].value, source=ORBIS, is_active=True)
                for profile in linked_profiles:
                    profile.accesses.update(end_datetime=timezone.now())
                count_deactivated = linked_profiles.update(is_active=False)
                self.log(f"{count_deactivated} ORBIS profiles have been deactivated for user `{p.identifier[0].value}`")
        self.log(f"{practitioner_res.count()} users have been synchronized with ORBIS")


    def sync_accesses(self, target_user: str = None):
        """
        - Fetch the PractitionerRole resource which represents an authorization for a Practitioner
          to perform a specific Role for a give period.
        - The roles fetched from FHIR are mapped to predefined roles in the DB.
        - For active PractitionerRoles, ensure having a role and a perimeter before creating a new access.
        - For later syncing, if a PractitionerRole gets deactivated, the corresponding Access is revoked.
        cf. https://hl7.org/fhir/R4/practitionerrole.html
        @return: None
        """
        if target_user:
            target_users = [target_user]
        else:
            target_users = list(User.objects.filter(delete_datetime__isnull=True).values_list("username", flat=True))

        users_batches = batched(target_users, n=100)

        count_orbis_accesses, count_new_accesses = 0, 0
        skipped_roles, missing_perimeters = set(), set()

        for batch in users_batches:
            res = self.fhir_client.resources("Practitioner")\
                                  .revinclude("PractitionerRole", "practitioner")\
                                  .search(identifier=",".join(batch))
            bundle = res.fetch_raw()

            if bundle.total > 0:
                for e in filter(lambda i: i.resource.resource_type == "PractitionerRole", bundle.entry):
                    count_orbis_accesses += 1
                    pr = e.resource
                    if pr.active:
                        default_end_datetime = timezone.now() + timezone.timedelta(days=settings.DEFAULT_ACCESS_VALIDITY_IN_DAYS)
                        fpr = FhirPractitionerRole(id=pr.id,
                                                   active=pr.active,
                                                   practitioner_id=pr.practitioner.to_resource().identifier[0].value,
                                                   perimeter_id=int(pr.organization.id),
                                                   role_name=pr.code[0].coding[0].code,
                                                   start_datetime=hasattr(pr.period, "start") and pr.period.start or None,
                                                   end_datetime=hasattr(pr.period, "end") and pr.period.end or default_end_datetime
                                                   )
                        profile = Profile.objects.filter(user_id=fpr.practitioner_id, source=ORBIS).first()
                        if profile is None:
                            profile = Profile.objects.create(user_id=fpr.practitioner_id,
                                                             source=ORBIS,
                                                             is_active=True)
                        role = self.get_mapped_role(fpr.role_name)
                        perimeter = Perimeter.objects.filter(id=fpr.perimeter_id).first()
                        if role is not None:
                            if perimeter is not None:
                                defaults = dict(source=ORBIS,
                                                external_id=fpr.id,
                                                role_id=role.id,
                                                profile_id=profile.id,
                                                perimeter_id=perimeter.id,
                                                start_datetime=fpr.start_datetime,
                                                end_datetime=fpr.end_datetime)
                                access, created = Access.objects.get_or_create(defaults=defaults, external_id=fpr.id)
                                if created:
                                    count_new_accesses += 1
                            else:
                                self.log(f"Could not find a match for the `perimeter` {fpr.perimeter_id=} to create access.")
                                missing_perimeters.add(fpr.perimeter_id)
                        else:
                            self.log(f"Could not find a match for the ORBIS role `{fpr.role_name}`")
                            skipped_roles.add(fpr.role_name)
                    else:
                        Access.objects.filter(external_id=pr.id).update(end_datetime=timezone.now())

        if skipped_roles:
            self.log(f"The following ORBIS roles were not correctly mapped: {skipped_roles}")
        if missing_perimeters:
            self.log(f"The following perimeters were not found: {missing_perimeters}")
        self.send_report_notification(skipped_roles, missing_perimeters, count_orbis_accesses, count_new_accesses)
        self.log(f"{count_orbis_accesses} accesses were fetched from ORBIS. "
                 f"{count_new_accesses} new accesses were created. "
                 f"{len(skipped_roles)} roles were skipped (no matching found).")


    @staticmethod
    def send_report_notification(skipped_roles, missing_perimeters, count_orbis_accesses, count_new_accesses):
        context = {"sync_time": datetime.now(),
                   "skipped_roles": sorted(skipped_roles),
                   "missing_perimeters": sorted(missing_perimeters),
                   "count_orbis_accesses": count_orbis_accesses,
                   "count_new_accesses": count_new_accesses,
                   }
        recipients_addresses = [a[1] for a in settings.ADMINS]
        email_notif = EmailNotification(subject="Rapport de synchronisation des accès ORBIS",
                                        to=recipients_addresses,
                                        html_template="sync_orbis_accesses_report.html",
                                        txt_template="sync_orbis_accesses_report.txt",
                                        context=context)
        email_notif.push()



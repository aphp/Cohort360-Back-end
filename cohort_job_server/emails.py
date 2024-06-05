from django.conf import settings

from admin_cohort.emails import EmailNotification
from admin_cohort.models import User


def send_email_notif_large_cohort_ready(cohort_name: str, cohort_id: str, cohort_owner: User) -> None:
    context = {"contact_email_address": settings.EMAIL_SUPPORT_CONTACT,
               "recipient_name": cohort_owner.display_name,
               "cohort_name": cohort_name,
               "cohort_url": f"{settings.FRONT_URL}/cohort/{cohort_id}"
               }
    email_notif = EmailNotification(subject="Votre cohorte est prête",
                                    to=cohort_owner.email,
                                    html_template="html/large_cohort_finished.html",
                                    txt_template="txt/large_cohort_finished.txt",
                                    context=context)
    email_notif.push()

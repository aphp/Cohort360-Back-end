import locale
import re
from datetime import timedelta
from typing import Tuple

from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from admin_cohort.models import User
from admin_cohort.settings import EMAIL_BACK_HOST_URL, EMAIL_SENDER_ADDRESS, \
    EMAIL_SUPPORT_CONTACT, EXPORT_DAYS_BEFORE_DELETE, EMAIL_REGEX_CHECK
from admin_cohort.types import JobStatus
from exports.models import ExportRequest, ExportType

locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')

BACKEND_URL = EMAIL_BACK_HOST_URL
SENDER_EMAIL_ADDR = EMAIL_SENDER_ADDRESS

KEY_DOWNLOAD_URL = "KEY_DOWNLOAD_URL"
KEY_COHORT_ID = "KEY_COHORT_ID"
KEY_NAME = "KEY_NAME"
KEY_ERROR_MESSAGE = "KEY_ERROR_MESSAGE"
KEY_CONTACT_MAIL = "KEY_CONTACT_MAIL"
KEY_CONTENT = "KEY_CONTENT"
KEY_DELETE_DATE = "KEY_DELETE_DATE"
KEY_DATABASE_NAME = "KEY_DATABASE_NAME"


def send_mail(msg: EmailMultiAlternatives):
    msg.send()


def replace_keys(txt: str, req: ExportRequest, is_html: bool = False) -> str:
    res = txt
    if txt.find(KEY_DOWNLOAD_URL) > -1:
        url = f"{BACKEND_URL}/accounts/login/?next=/exports/{req.id}/download/"
        res = res.replace(KEY_DOWNLOAD_URL,
                          f"<a href='{url}' class=3D'OWAAutoLink'>Télécharger</a>" if is_html else url)
    keys_vals = {KEY_COHORT_ID: req.cohort_id,
                 KEY_NAME: req.creator_fk and req.creator_fk.displayed_name or None,
                 KEY_ERROR_MESSAGE: req.request_job_fail_msg,
                 KEY_CONTACT_MAIL: EMAIL_SUPPORT_CONTACT,
                 KEY_DATABASE_NAME: req.target_name,
                 KEY_DELETE_DATE: (timezone.now().date() +
                                   timedelta(days=int(EXPORT_DAYS_BEFORE_DELETE))).strftime("%d %B, %Y")
                 }
    for k, v in keys_vals.items():
        res = res.replace(str(k), str(v))
    return res


def get_base_templates() -> Tuple[str, str]:
    with open("exports/email_templates/base_template.html") as f:
        html_content = "\n".join(f.readlines())

    with open("exports/email_templates/base_template.txt") as f:
        txt_content = "\n".join(f.readlines())

    return html_content, txt_content


def check_email_address(user: User):
    """
    Check that the Provider has a correct email address
    @param user:
    @type Provider:
    @return:
    @rtype:
    """
    if user.email is None or not len(user.email):
        raise ValidationError(f"L'utilisateur {user.displayed_name} "
                              f"n'a pas d'email fourni,"
                              f" merci de contacter un administrateur")

    if not re.match(EMAIL_REGEX_CHECK, user.email):
        raise ValidationError(f"L'utilisateur a une adresse email "
                              f"incorrecte ({user.email}). Notez "
                              f"qu'elle doit satisfaire la "
                              f"RegEx {EMAIL_REGEX_CHECK}. Merci de contacter "
                              f"un administrateur.")


def send_failed_email(req: ExportRequest, email_address: str):
    with open("exports/email_templates/resultat_requete_echec.txt") as f:
        txt_content = "\n".join(f.readlines())

    with open("exports/email_templates/resultat_requete_echec.html") as f:
        html_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    subject, from_email = f"[Cohorte {req.cohort_id}] Votre demande d'export " \
                          f"n'a pas abouti", SENDER_EMAIL_ADDR
    msg = EmailMultiAlternatives(
        subject=subject, body=replace_keys(txt_mail, req),
        from_email=from_email, to=[email_address]
    )

    msg.attach_alternative(replace_keys(html_mail, req, True), "text/html")
    msg.attach_file('exports/email_templates/logoCohort360.png')
    send_mail(msg)

    # send_mail(
    #     subject, replace_keys(txt_mail, req), from_email,
    #     [email_address], fail_silently=False,
    #     html_message=replace_keys(html_mail, req, True)
    # )


def send_success_email(req: ExportRequest, email_address: str):
    html_path = f"exports/email_templates/resultat_requete_succes" \
                f"{'_hive' if req.output_format == ExportType.HIVE else ''}" \
                f".html"
    txt_path = f"exports/email_templates/resultat_requete_succes" \
               f"{'_hive' if req.output_format == ExportType.HIVE else ''}" \
               f".txt"

    with open(html_path) as f:
        html_content = "\n".join(f.readlines())

    with open(txt_path) as f:
        txt_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    subject = f"[Cohorte {req.cohort_id}] Export terminé"
    from_email = SENDER_EMAIL_ADDR

    msg = EmailMultiAlternatives(
        subject=subject, body=replace_keys(txt_mail, req),
        from_email=from_email, to=[email_address]
    )

    msg.attach_alternative(replace_keys(html_mail, req, True), "text/html")
    msg.attach_file('exports/email_templates/logoCohort360.png')
    send_mail(msg)

    # send_mail(
    #     subject, replace_keys(txt_mail, req),
    #     from_email, [email_address], fail_silently=False,
    #     html_message=replace_keys(html_mail, req, True)
    # )


def email_info_request_done(req: ExportRequest):
    """
    Read the templates for a finished request email and send it to the user
    binded to it
    @param req:
    @type req:
    @return:
    @rtype:
    """
    check_email_address(req.owner)

    if req.request_job_status == JobStatus.finished:
        send_success_email(req, req.owner.email)
    elif req.request_job_status in [JobStatus.failed, JobStatus.cancelled]:
        send_failed_email(req, req.owner.email)


def email_info_request_confirmed(req: ExportRequest, email_address: str):
    """
    Send an email to the user informing that its request was well received
    @param req:
    @type req:
    @param email_address:
    @type email_address:
    @return:
    @rtype:
    """
    html_path = f"exports/email_templates/confirmation_de_requete" \
                f"{'_hive' if req.output_format == ExportType.HIVE else ''}" \
                f".html"
    txt_path = f"exports/email_templates/confirmation_de_requete" \
               f"{'_hive' if req.output_format == ExportType.HIVE else ''}" \
               f".txt"
    with open(html_path) as f:
        html_content = "\n".join(f.readlines())

    with open(txt_path) as f:
        txt_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    action = "Demande d'export CSV reçue" \
        if req.output_format == ExportType.CSV \
        else "Demande reçue de transfert en environnement Jupyter"

    subject = f"[Cohorte {req.cohort_id}] {action}"
    from_email = SENDER_EMAIL_ADDR

    msg = EmailMultiAlternatives(
        subject=subject, body=replace_keys(txt_mail, req),
        from_email=from_email, to=[email_address]
    )

    msg.attach_alternative(replace_keys(html_mail, req, True), "text/html")
    msg.attach_file('exports/email_templates/logoCohort360.png')
    send_mail(msg)

    # send_mail(
    #     subject, replace_keys(txt_mail, req), from_email,
    #     [email], fail_silently=False,
    #     html_message=replace_keys(html_mail, req, True)
    # )
    return


def email_info_request_deleted(req: ExportRequest, email_address: str):
    """
    Send an email to the user informing that its request was deleted
    @param req:
    @type req:
    @param email_address:
    @type email_address:
    @return:
    @rtype:
    """
    with open("exports/email_templates/confirmation_suppression.html") as f:
        html_content = "\n".join(f.readlines())

    with open("exports/email_templates/confirmation_suppression.txt") as f:
        txt_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    subject, from_email = f"[Cohorte {req.cohort_id}] Confirmation " \
                          f"de suppression de fichier", SENDER_EMAIL_ADDR

    msg = EmailMultiAlternatives(
        subject=subject, body=replace_keys(txt_mail, req),
        from_email=from_email, to=[email_address]
    )

    msg.attach_alternative(replace_keys(html_mail, req, True), "text/html")
    msg.attach_file('exports/email_templates/logoCohort360.png')
    send_mail(msg)

    # send_mail(
    #     subject, replace_keys(txt_mail, req), from_email, [email_address],
    #     fail_silently=False, html_message=replace_keys(html_mail, req, True)
    # )
    return

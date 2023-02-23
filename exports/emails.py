import locale
import logging
import re
from datetime import timedelta
from smtplib import SMTPException
from typing import Tuple

from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from admin_cohort.models import User
from admin_cohort.settings import EMAIL_BACK_HOST_URL, EMAIL_SENDER_ADDRESS, EMAIL_SUPPORT_CONTACT, \
    DAYS_TO_DELETE_CSV_FILES, EMAIL_REGEX_CHECK
from admin_cohort.types import JobStatus
from .models import ExportRequest
from .types import ExportType

locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')

BACKEND_URL = EMAIL_BACK_HOST_URL
SENDER_EMAIL_ADDR = EMAIL_SENDER_ADDRESS
TEXT_HTML = "text/html"

COHORT360_LOGO = "exports/email_templates/logoCohort360.png"

KEY_DOWNLOAD_URL = "KEY_DOWNLOAD_URL"
KEY_COHORT_ID = "KEY_COHORT_ID"
KEY_NAME = "KEY_NAME"
KEY_ERROR_MESSAGE = "KEY_ERROR_MESSAGE"
KEY_CONTACT_MAIL = "KEY_CONTACT_MAIL"
KEY_CONTENT = "KEY_CONTENT"
KEY_DELETE_DATE = "KEY_DELETE_DATE"
KEY_DATABASE_NAME = "KEY_DATABASE_NAME"
KEY_SELECTED_TABLES = "KEY_SELECTED_TABLES"

_logger = logging.getLogger('django.request')


def send_email(msg: EmailMultiAlternatives):
    msg.send()


def get_selected_tables(req: ExportRequest, is_html=False):
    tables = []
    for t in req.tables.all():
        item = is_html and f"<li>{t.omop_table_name}</li>" or f"- {t.omop_table_name}"
        tables.append(item)
    return is_html and f"<ul>{''.join(tables)}</ul>" or "\n".join(tables)


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
                                   timedelta(days=int(DAYS_TO_DELETE_CSV_FILES))).strftime("%d %B, %Y"),
                 KEY_SELECTED_TABLES: get_selected_tables(req, is_html=is_html)
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
    if not user.email:
        raise ValidationError(f"No email address is configured for user {user.displayed_name}. "
                              f"Please contact an administrator")
    if not re.match(EMAIL_REGEX_CHECK, user.email):
        raise ValidationError(f"Invalid email address ({user.email}). Must match the RegEx {EMAIL_REGEX_CHECK}. "
                              f"Please contact an administrator.")


def send_failed_email(req: ExportRequest, email_address: str):
    with open("exports/email_templates/resultat_requete_echec.txt") as f:
        txt_content = "\n".join(f.readlines())

    with open("exports/email_templates/resultat_requete_echec.html") as f:
        html_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    subject = f"[Cohorte {req.cohort_id}] Votre demande d'export n'a pas abouti"
    msg = EmailMultiAlternatives(subject=subject,
                                 body=replace_keys(txt_mail, req),
                                 from_email=SENDER_EMAIL_ADDR,
                                 to=[email_address])

    msg.attach_alternative(content=replace_keys(html_mail, req, is_html=True), mimetype=TEXT_HTML)
    msg.attach_file(COHORT360_LOGO)
    send_email(msg)


def send_success_email(req: ExportRequest, email_address: str):
    hive_suffix = req.output_format == ExportType.HIVE and '_hive' or ''
    html_path = f"exports/email_templates/resultat_requete_succes{hive_suffix}.html"
    txt_path = f"exports/email_templates/resultat_requete_succes{hive_suffix}.txt"

    with open(html_path) as f:
        html_content = "\n".join(f.readlines())

    with open(txt_path) as f:
        txt_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    subject = f"[Cohorte {req.cohort_id}] Export terminé"

    msg = EmailMultiAlternatives(subject=subject,
                                 body=replace_keys(txt_mail, req),
                                 from_email=SENDER_EMAIL_ADDR,
                                 to=[email_address])

    msg.attach_alternative(content=replace_keys(html_mail, req, is_html=True), mimetype=TEXT_HTML)
    msg.attach_file(COHORT360_LOGO)
    send_email(msg)


def email_info_request_done(req: ExportRequest):
    check_email_address(req.owner)
    try:
        if req.request_job_status == JobStatus.finished:
            send_success_email(req, req.owner.email)
        elif req.request_job_status in [JobStatus.failed, JobStatus.cancelled]:
            send_failed_email(req, req.owner.email)
    except (SMTPException, TimeoutError):
        except_msg = f"Could not send export email - request status was '{req.request_job_status}'"
        _logger.exception(f"{except_msg} - Mark it as '{JobStatus.failed}'")
        req.request_job_status = JobStatus.failed
        req.request_job_fail_msg = except_msg
        req.save()
        return
    req.is_user_notified = True
    req.save()


def email_info_request_confirmed(req: ExportRequest, email_address: str):
    hive_suffix = req.output_format == ExportType.HIVE and '_hive' or ''
    html_path = f"exports/email_templates/confirmation_de_requete{hive_suffix}.html"
    txt_path = f"exports/email_templates/confirmation_de_requete{hive_suffix}.txt"

    with open(html_path) as f:
        html_content = "\n".join(f.readlines())

    with open(txt_path) as f:
        txt_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    action = req.output_format == ExportType.CSV and "Demande d'export CSV reçue" or "Demande reçue de transfert en environnement Jupyter"
    subject = f"[Cohorte {req.cohort_id}] {action}"

    msg = EmailMultiAlternatives(subject=subject,
                                 body=replace_keys(txt_mail, req),
                                 from_email=SENDER_EMAIL_ADDR,
                                 to=[email_address])

    msg.attach_alternative(content=replace_keys(html_mail, req, is_html=True), mimetype=TEXT_HTML)
    msg.attach_file(COHORT360_LOGO)
    send_email(msg)


def email_info_request_deleted(req: ExportRequest, email_address: str):
    with open("exports/email_templates/confirmation_suppression.html") as f:
        html_content = "\n".join(f.readlines())

    with open("exports/email_templates/confirmation_suppression.txt") as f:
        txt_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    subject = f"[Cohorte {req.cohort_id}] Confirmation de suppression de fichier"

    msg = EmailMultiAlternatives(subject=subject,
                                 body=replace_keys(txt_mail, req),
                                 from_email=SENDER_EMAIL_ADDR,
                                 to=[email_address])

    msg.attach_alternative(content=replace_keys(html_mail, req, is_html=True), mimetype=TEXT_HTML)
    msg.attach_file(COHORT360_LOGO)
    send_email(msg)

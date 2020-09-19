"""Helping utilities for members."""

import logging
import os
import re

import certg
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def clean_double_empty_lines(oldtext):
    while True:
        newtext = re.sub("\n *?\n *?\n", "\n\n", oldtext)
        if newtext == oldtext:
            return newtext
        oldtext = newtext


def build_debt_string(debt):
    """Build a nice string to represent the debt."""
    if not debt:
        return "-"

    # convert tuples to nice string format (only first 3, the used ones)
    debt_nicer = ["{}-{:02d}".format(*d) for d in debt[:3]]
    exceeding = "" if len(debt) <= 3 else ", ..."
    result = "{} ({}{})".format(len(debt), ", ".join(debt_nicer), exceeding)
    return result


def generate_member_letter(member):
    """Generate the letter to be signed by a wanna-be member."""
    letter_svg_template = os.path.join(
        os.path.dirname(__file__), 'templates', 'members', 'carta.svg')
    path_prefix = "/tmp/letter"
    person = member.person
    person_info = {
        'tiposocie': member.category.name,
        'nombre': person.first_name,
        'apellido': person.last_name,
        'dni': person.document_number,
        'email': person.email,
        'nacionalidad': person.nationality,
        'estadocivil': person.marital_status,
        'profesion': person.occupation,
        'fechanacimiento': person.birth_date.strftime("%Y-%m-%d"),
        'domicilio': person.street_address,
        'ciudad': person.city,
        'codpostal': person.zip_code,
        'provincia': person.province,
        'pais': person.country,
    }

    # this could be optimized to generate all PDFs at once, but we're fine so far
    (letter_filepath,) = certg.process(
        letter_svg_template, path_prefix, "dni", [person_info], images=None)
    return letter_filepath


def send_email(member, subject, text, attachment=None, cc=None):
    """Send a mail to a member."""
    text = clean_double_empty_lines(text)
    recipient = f"{member.entity.full_name} <{member.entity.email}>"
    if cc is None:
        cc = []

    mail = EmailMessage(subject, text, settings.EMAIL_FROM, [recipient], cc=cc)
    if attachment is not None:
        mail.attach_file(attachment)
    mail.send()


def send_missing_info_mail(member):
    """Send a mail to a member with all missing information.

    This is used by reports, or when the user initially subscribes, or could be triggered from
    anywhere, as it only sends what is missing.
    """
    mail_subject = "Continuación del trámite de inscripción a la Asociación Civil Python Argentina"

    # create the mail text from the template
    missing_info = member.get_missing_info()
    missing_info['annual_fee'] = member.category.fee * 12
    missing_info['member'] = member
    missing_info['on_purpose_missing_var'] = "ERROR"
    text = render_to_string('members/mail_missing.txt', missing_info)
    if 'ERROR' in text:
        # badly built template
        msg = "Error when building the report missing mail result, info: {}".format(missing_info)
        raise ValueError(msg)

    # if missing the signed letter, produce it
    if missing_info['missing_signed_letter']:
        letter_filepath = generate_member_letter(member)
    else:
        letter_filepath = None

    # send the mail
    try:
        send_email(member, mail_subject, text, attachment=letter_filepath)
    finally:
        if letter_filepath is not None:
            os.unlink(letter_filepath)

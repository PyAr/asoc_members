"""Helping utilities for members."""

import logging
import os
import re

import certg
from django.conf import settings
from django.core.mail import EmailMessage

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


def send_email(member, subject, text, attachment=None):
    """Send a mail to a member."""
    text = clean_double_empty_lines(text)
    recipient = f"{member.entity.full_name} <{member.entity.email}>"

    mail = EmailMessage(subject, text, settings.EMAIL_FROM, [recipient])
    if attachment is not None:
        mail.attach_file(attachment)
    mail.send()

import re
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.timezone import now

from members import logic

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


def get_yearmonth(request):
    try:
        year = int(request.GET['limit_year'])
        month = int(request.GET['limit_month'])
    except (KeyError, ValueError):
        # get by default one month before now, as it's the first month not really
        # paid (current month is not yet finished)
        currently = now()
        year = currently.year
        month = currently.month - 1
        if month <= 0:
            year -= 1
            month += 12
    return year, month


def sendmail_missing_info(member):
    """
    Generate email with application letter and sent it.
    """
    EMAIL_SUBJECT = "Continuación del trámite de inscripción a la " \
        "Asociación Civil Python Argentina"

    missing_info = member._analyze()
    text = render_to_string('members/mail_missing.txt', missing_info)
    text = clean_double_empty_lines(text)
    if 'ERROR' in text:
        # badly built template
        text_err = "Error when building the report missing mail result, info: %s" % missing_info
        logger.error(text_err)
        raise Exception(text_err)

    # build the mail
    recipient = f"{member.entity.full_name} <{member.entity.email}>"
    mail = EmailMessage(EMAIL_SUBJECT, text, settings.EMAIL_FROM, [recipient])
    # if missing the signed letter, produce it and attach it
    if missing_info['missing_signed_letter']:
        mail.attach_file(member.application_letter.path)
    mail.send()


def sendmail_about_debts(member, limit_year, limit_month):
    """
    Generate email with debts information.
    """
    EMAIL_SUBJECT = "Cuotas adeudadas a la Asociación Civil Python Argentina"

    debt = logic.get_debt_state(member, limit_year, limit_month)
    debt_info = {
        'debt': build_debt_string(debt),
        'member': member,
        'annual_fee': member.category.fee * 12,
        'on_purpose_missing_var': "ERROR",
    }
    text = render_to_string('members/mail_indebt.txt', debt_info)
    text = clean_double_empty_lines(text)
    if 'ERROR' in text:
        # badly built template
        text_ext = "Error when building the report missing mail result, info: %s" % debt_info
        logger.error(text_ext)
        raise Exception(text_ext)

    recipient = f"{member.entity.full_name} <{member.entity.email}>"
    mail = EmailMessage(EMAIL_SUBJECT, text, settings.EMAIL_FROM, [recipient])
    mail.send()

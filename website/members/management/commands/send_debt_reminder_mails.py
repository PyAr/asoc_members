"""Command to send debt reminders to all who has debts."""

import datetime

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from members import logic, utils
from members.models import Member, Person

MAIL_SUBJECT = "Cuotas adeudadas a la Asociación Civil Python Argentina"


class Command(BaseCommand):
    help = "Send the debt reminder mails to whom corresponds"

    def handle(self, *args, **options):
        currently = datetime.datetime.now()
        limit_year, limit_month = logic.decrement_year_month(currently.year, currently.month)

        members = (
            Member.objects
            .filter(legal_id__isnull=False, category__fee__gt=0, shutdown_date__isnull=True)
            .order_by('legal_id')
            .all()
        )
        mail_data = []
        for member in members:
            if not isinstance(member.entity, Person):
                continue

            debt = logic.get_debt_state(member, limit_year, limit_month)
            if not debt:
                continue

            debt_info = {
                'debt': utils.build_debt_string(debt),
                'member': member,
                'annual_fee': member.category.fee * 12,
                'on_purpose_missing_var': "ERROR",
            }
            text = render_to_string('members/mail_indebt.txt', debt_info)
            if 'ERROR' in text:
                # badly built template
                raise ValueError("Problems building the mail text; info: {}".format(debt_info))
            mail_data.append((member, text))

        print("Found {} members in debt".format(len(mail_data)))

        for member, text in mail_data:
            print(f"Sending mail to {member.entity.full_name} <{member.entity.email}>")

            try:
                utils.send_email(member, MAIL_SUBJECT, text)
            except Exception as err:
                print("    problem:", repr(err))
            else:
                print("    ok")

        print("Done")

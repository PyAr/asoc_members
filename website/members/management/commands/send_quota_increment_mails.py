"""Command to easily send a lot of mails when quota increments.

Procedure, in general:

1. Get NEW Mercadopago links to update MP_* constants below

2. Put those links also in...
       website/members/templates/members/mail_missing.txt
       website/members/templates/members/mail_indebt.txt

3. Update the NEW_FEE_AMOUNT dict here.

NOTE: quota amounts in the DB are NOT updated yet!

4. Run this command

        ./manage.py send_quota_increment_mails

5. wait a week or so

Now, the following changes should happen "fast"...

6.1. run the get_mercadopago_payments last time for old amounts

6.2. update quota amounts in the DB

6.3. update values for old Mercadopago subscriptions (that will co-exist with new ones)

6.4. run the get_mercadopago_payments again
"""

import collections
import datetime

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand

from members import logic
from members.models import Member, Quota, Category

# These are the NEXT amounts, NOT what is currently stored in the DB (see the above
# indications: the DB will be updated later)
NEW_FEE_AMOUNT = {
    Category.SUPPORTER: 200,
    Category.ACTIVE: 400,
}

# MercadoPago URLs
MP_MONTHLYDEBIT_SUPPORTER = "http://mpago.la/1EH9Tq"
MP_MONTHLYDEBIT_ACTIVE = "http://mpago.la/2yb62i"
MP_FULLYEAR_SUPPORTER = "https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=282968656-0a979fe3-9e1d-4223-b5c3-1db274690afa"  # NOQA
MP_FULLYEAR_ACTIVE = "https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=282968656-74cdbc78-c57f-491c-b540-48e4d4878304"  # NOQA
MP_LINKS = {
    Category.SUPPORTER: (MP_MONTHLYDEBIT_SUPPORTER, MP_FULLYEAR_SUPPORTER),
    Category.ACTIVE: (MP_MONTHLYDEBIT_ACTIVE, MP_FULLYEAR_ACTIVE),
}

# mail texts
MAIL_SUBJECT = "Cambio de monto en la cuota social de socies {member_type}"
MAIL_TEXT = """\
Hola {person_name}!

Te mando este mail porque en la última Asamblea de socies se aprobó que el
monto para socies {member_type} es ahora de ${new_quota_amount} por mes.

Si vos ya estás pagando por débito automático, no tenés que hacer nada, dentro
de una semana nosotros actualizamos el monto de esa suscripción y el resto es
todo... bueno... automático, justamente.

Por otro lado, si querés empezar a pagar por débito automático desde ahora,
el link es:

    {monthly_debit_url}

Para pagar el año entero con tarjetas de crédito, débito, pagofácil, rapipago, etc.,
el enlace es:

    {year_payment_url}

Si pagás por transferencia, obviamente el monto lo calculás en el momento (por este
medio es mínimo un año), los datos son:

    Asociación Civil Python Argentina
    Banco Credicoop
    Cuenta Corriente en pesos
    Nro. 191-153-009748/3
    CBU 19101530-55015300974832

{debt_status}
Cualquier duda avisame.

Gracias, saludos!

--
.   Lalita
.
Asociación Civil Python Argentina
http://ac.python.org.ar/

(claro, este mail es automático, soy une bot, pero contestá el mail sin problemas que
le va a llegar al humane correspondiente)
"""

DEBT_NO = """\
Tené en cuenta que estás al día con las cuotas, ¡gracias por eso!
"""
DEBT_YES = """\
Aprovecho y te recuerdo que debés cuotas sociales, la última que abonaste
fue {month_name} {year}.
"""
DEBT_ALL = """\
Aprovecho y te recuerdo todavía no abonaste ninguna cuota social :(.
"""

MONTHS = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Septiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre',
}

MEMBERS_TRANSLATION = {
    Category.SUPPORTER: "Adherentes",
    Category.ACTIVE: "Actives"
}


class Command(BaseCommand):
    help = "Send the quota increment mails to all members"

    def handle(self, *args, **options):
        # Get supporter and active members.
        categories = [Category.SUPPORTER, Category.ACTIVE]
        members = (
            Member.objects
            .filter(
                category__name__in=categories,
                legal_id__isnull=False,
                shutdown_date__isnull=True,
            )
            .order_by('legal_id')
            .all())
        count = collections.Counter(m.category.name for m in members)
        print("Found {} members: {}".format(len(members), count))

        # To check if in debt, get one month before now, as it would be the first not really
        # paid month (current month is not yet finished)
        currently = datetime.datetime.now()
        limit_year, limit_month = logic.decrement_year_month(currently.year, currently.month)

        mail_data = []
        for member in members:
            print("Processing member {}".format(member))

            debt = logic.get_debt_state(member, limit_year, limit_month)
            if debt:
                quotas = list(Quota.objects.filter(member=member).order_by('year', 'month').all())
                if quotas:
                    latest_quota = quotas[-1]
                    month_name = MONTHS[latest_quota.month]
                    debt_status = DEBT_YES.format(year=latest_quota.year, month_name=month_name)
                else:
                    debt_status = DEBT_ALL
            else:
                debt_status = DEBT_NO

            # mail stuff
            mail = {}
            mail_data.append(mail)
            translated_type = MEMBERS_TRANSLATION[member.category.name]
            mail['subject'] = MAIL_SUBJECT.format(member_type=translated_type)
            mail['recipient'] = member.person.email
            monthly_debit_url, year_payment_url = MP_LINKS[member.category.name]
            mail['text'] = MAIL_TEXT.format(
                member_type=translated_type, new_quota_amount=NEW_FEE_AMOUNT[member.category.name],
                monthly_debit_url=monthly_debit_url, year_payment_url=year_payment_url,
                debt_status=debt_status, person_name=member.person.first_name)

        print("Sending mails...")
        for info in mail_data:
            recipient = info['recipient']
            print("    ", recipient)
            mail = EmailMessage(info['subject'], info['text'], settings.EMAIL_FROM, [recipient])
            mail.send()
        print("Done")

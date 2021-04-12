"""Command to send debt reminders to all who has debts."""

import collections
import datetime

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand

from members import logic
from members.models import Member, Quota, Category

MAIL_SUBJECT = "Cuotas adeudadas a la Asociación Civil Python Argentina"



class Command(BaseCommand):
    help = "Send the debt reminder mails to whom corresponds"

    def handle(self, *args, **options):
        currently = datetime.datetime.now()
        limit_year, limit_month = logic.decrement_year_month(currently.year, currently.month)

        # get those already confirmed members
        members = (Member.objects
            .filter(legal_id__isnull=False, category__fee__gt=0, shutdown_date__isnull=True)
            .order_by('legal_id')
            .all())

        debts = []
        for member in members:
            debt = logic.get_debt_state(member, limit_year, limit_month)
            if debt:
                debts.append((member, utils.build_debt_string(debt)))
        print("Found {} members in debt".format(len(debts))

        #context = {
        #    'debts': debts,
        #    'limit_year': limit_year,
        #    'limit_month': limit_month,
        #}
        #return render(request, 'members/report_debts.html', context)


        mail_data = []
        #for member in members:

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




----




    def post(self, request):
        raw_sendmail = parse.parse_qs(request.body)[b'sendmail']
        to_send_mail_ids = map(int, raw_sendmail)
        limit_year, limit_month = self._get_yearmonth(request)

        sent_error = 0
        sent_ok = 0
        tini = time.time()
        errors_code = str(uuid.uuid4())
        for member_id in to_send_mail_ids:
            member = Member.objects.get(id=member_id)

            debt = logic.get_debt_state(member, limit_year, limit_month)
            debt_info = {
                'debt': utils.build_debt_string(debt),
                'member': member,
                'annual_fee': member.category.fee * 12,
                'on_purpose_missing_var': "ERROR",
            }
            text = render_to_string('members/mail_indebt.txt', debt_info)
            if 'ERROR' in text:
                # badly built template
                logger.error(
                    "Error when building the report missing mail result, info: %s", debt_info)
                return HttpResponse("Error al armar la página")
            try:
                utils.send_email(member, self.MAIL_SUBJECT, text)
            except Exception as err:
                sent_error += 1
                logger.exception(
                    "Problems sending email [%s] to member %s: %r", errors_code, member, err)
            else:
                sent_ok += 1
        deltat = time.time() - tini

        context = {
            'sent_ok': sent_ok,
            'sent_error': sent_error,
            'errors_code': errors_code,
            'deltamsec': int(deltat * 1000),
        }
        return render(request, 'members/mail_sent.html', context)



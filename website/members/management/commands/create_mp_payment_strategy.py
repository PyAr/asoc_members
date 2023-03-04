import datetime

from django.core.management.base import BaseCommand, CommandError

from members.models import Member, PaymentStrategy

PLATFORMS = {
    'credit': PaymentStrategy.CREDIT,
    'mercadopago': PaymentStrategy.MERCADO_PAGO,
    'todopago': PaymentStrategy.TODO_PAGO,
    'transfer': PaymentStrategy.TRANSFER,
}


class Command(BaseCommand):
    help = "Helper to create a payment strategy for Mercadopago"

    def add_arguments(self, parser):
        parser.add_argument('dni', type=str)
        parser.add_argument('payer_id', type=str)

    def handle(self, *args, **options):
        payer_id = options["payer_id"]
        dni = options["dni"]

        try:
            member = Member.objects.get(person__document_number=dni)
        except Member.DoesNotExist:
            raise CommandError("There is no member whose person has that document number.")

        print("Member:", member)
        assert member.patron is not None

        if member.first_payment_year is None:
            print("Setting first payment year and month")
            today = datetime.date.today()
            member.first_payment_year = today.year
            member.first_payment_month = today.month
            member.save()

        payment_strategy = PaymentStrategy(
            platform=PaymentStrategy.MERCADO_PAGO,
            id_in_platform=payer_id,
            patron=member.patron,
        )
        payment_strategy.save()
        print("Strategy created")

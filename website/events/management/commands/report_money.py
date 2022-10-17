import enum
from decimal import Decimal

from django.core.management.base import BaseCommand

from events.models import Event, Expense, Invoice, Sponsoring

from rapidtables import make_table


class Command(BaseCommand):
    help = "Produce money reports"

    def add_arguments(self, parser):
        parser.add_argument('name_parts', nargs='+', type=str)

    def handle(self, *args, **options):
        name_parts = options['name_parts']

        # search
        events = Event.objects.all()
        matching_events = []
        for event in events:
            if all(p in event.name for p in name_parts):
                matching_events.append(event)

        # error if none or too many
        if not matching_events:
            print("ERROR: no matching events! the available ones are:")
            for event in events:
                print("    ", repr(event.name))
        elif len(matching_events) > 1:
            print("ERROR: too many matching events! found these:")
            for event in matching_events:
                print("    ", repr(event.name))
        else:
            main(matching_events[0])


class PaymentState(enum.Enum):
    not_invoiced = "no invoice"
    complete = "✓"
    partial = "partial"
    missing = "no payment"


def show_title(title):
    """Show spaced title."""
    print("\n\n" + title + "\n")


def show_table(title, table):
    """Show table nicely."""
    show_title(title)
    for line in make_table(table).split("\n"):
        print("    " + line)


def process_incomes(event):
    """Process and show incomes."""
    income_totals = dict(available=0, pending=0)
    sponsorings = Sponsoring.objects.filter(sponsorcategory__event=event, close=False).all()
    if not sponsorings:
        print("WARNING!!! sponsorings not found")
        return income_totals

    income_data = []
    for sponsoring in sponsorings:
        try:
            invoice = Invoice.objects.get(sponsoring=sponsoring)
        except Invoice.DoesNotExist:
            payment_state = PaymentState.not_invoiced
        else:
            if invoice.complete_payment:
                payment_state = PaymentState.complete
            elif invoice.partial_payment:
                payment_state = PaymentState.partial
            else:
                payment_state = PaymentState.missing

        # sponsor info
        sponsor_info = "{} ({})".format(
            sponsoring.sponsor.organization_name, sponsoring.sponsorcategory.name)

        # give priority to the real final amount, if present, as in some payments (e.g.
        # international ones) the final amount is different
        amount = invoice.amount
        if invoice.real_final_amount is not None:
            amount = invoice.real_final_amount

        income_data.append({
            'amount': amount,
            'payment': payment_state.value,
            'sponsorship': sponsor_info,
        })

        total = "available" if payment_state == PaymentState.complete else "pending"
        income_totals[total] = income_totals[total] + amount

    show_table("Detailed sponsorships status:", income_data)
    return income_totals


def process_expenses(event):
    """Process and show expenses."""
    expense_totals = dict(base=0, iva=0)
    expenses = Expense.objects.filter(event=event).all()
    if not expenses:
        print("WARNING!!! expenses not found")
        return expense_totals

    expense_data = []
    for expense in expenses:
        if expense.is_cancelled:
            continue
        description = "{} ({}, {})".format(
            expense.description, expense.invoice_date, expense.category)
        if expense.invoice_type == Expense.INVOICE_TYPE_A:
            amount_base = round(expense.amount / Decimal("1.21"), 2)
            amount_iva = expense.amount - amount_base
        else:
            amount_base = expense.amount
            amount_iva = 0

        expense_data.append({
            'amount': expense.amount,
            'base': amount_base,
            'IVA': amount_iva,
            'invoice': expense.invoice_type,
            'description': description,
        })

        expense_totals['base'] = expense_totals['base'] + amount_base
        expense_totals['iva'] = expense_totals['iva'] + amount_iva

    show_table("Detailed expenses:", expense_data)
    return expense_totals


def main(event):
    """Main entry point."""
    print("\n### Money report for event {!r}".format(event.name))

    # process invoices and show summary
    income_totals = process_incomes(event)
    show_title("Liquidity:")
    income_base = income_totals['available']
    income_iva = round(income_base * Decimal(".21"), 2)
    commission_amount = round((income_base + income_iva) * event.commission / 100, 2)
    print("    Income:     {:12,.2f}".format(income_base))
    print("       + IVA:   {:12,.2f}".format(income_iva))
    print("    Pending:    {:12,.2f}".format(income_totals['pending']))
    print("    Commission: {:12,.2f}".format(commission_amount))

    # process expenses and show summary
    expense_totals = process_expenses(event)
    show_title("Expenses:")
    print("    Base amount:  {:12,.2f}".format(expense_totals['base']))
    print("    Discrim. IVA: {:12,.2f}".format(expense_totals['iva']))

    # show available money (most important indicator) and remaining iva (just a control for a
    # number that may be zero if all expenses are invoice "A", never negative); the available
    # money is the input (base, no IVA considered), minus the expenses (which for invoices A
    # already have the IVA discounted), minus the commission
    show_title("Control:")
    available = income_base - expense_totals['base'] - commission_amount
    remaining_iva = income_iva - expense_totals['iva']
    print("    Available:     {:12,.2f}".format(available))
    print("    Remaining IVA: {:12,.2f}".format(remaining_iva))

    # grand numbers for AC control (not thought to be shown to organizers)
    show_title("AC results:")
    bank_movements = income_base + income_iva + expense_totals['base'] + expense_totals['iva']
    bank_loss = round(bank_movements * Decimal(".006"), 2)
    print("    Commission: {:12,.2f}".format(commission_amount))
    print("    Bank loss:  {:12,.2f}".format(bank_loss))
    print("    Total:      {:12,.2f}".format(commission_amount - bank_loss))

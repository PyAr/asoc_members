from django import template
from decimal import Decimal

register = template.Library()


@register.filter(name='money_format')
def money_format(value):
    if value is None or value == '' or value == '-':
        return "-"
    try:
        val = Decimal(str(value))
    except (ValueError, TypeError):
        return str(value)
    
    # Format to 2 decimal places with thousand and decimal separators: 1,234,567.89
    formatted = f"{val:,.2f}"
    # Convert to Argentine format: 1.234.567,89
    trans = formatted.translate(str.maketrans({',': '.', '.': ','}))
    return trans

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _to_decimal(value):
    if value in (None, ""):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


@register.filter
def naira(value):
    amount = _to_decimal(value)
    if amount is None:
        return f"₦{value}"
    rounded = amount.quantize(Decimal("0.01"))
    if rounded == rounded.to_integral():
        return f"₦{int(rounded):,}"
    return f"₦{rounded:,.2f}"

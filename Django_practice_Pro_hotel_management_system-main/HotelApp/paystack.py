from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings


class PaystackError(Exception):
    pass


def paystack_is_configured() -> bool:
    return bool(settings.PAYSTACK_SECRET_KEY)


def amount_to_subunit(amount: Decimal) -> int:
    decimal_amount = Decimal(str(amount))
    return int((decimal_amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def initialize_transaction(
    *,
    email: str,
    amount: Decimal,
    reference: str,
    callback_url: str,
    metadata: dict | None = None,
    first_name: str = "",
    last_name: str = "",
) -> dict:
    payload = {
        "email": email,
        "amount": str(amount_to_subunit(amount)),
        "reference": reference,
        "callback_url": callback_url,
        "currency": settings.PAYSTACK_CURRENCY,
        "metadata": metadata or {},
    }
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name

    response = _paystack_request("/transaction/initialize", method="POST", payload=payload)
    data = response.get("data") or {}
    if not response.get("status") or not data.get("authorization_url"):
        raise PaystackError(response.get("message") or "Paystack could not initialize this payment.")
    return data


def verify_transaction(reference: str) -> dict:
    response = _paystack_request(f"/transaction/verify/{quote(reference)}")
    if not response.get("status"):
        raise PaystackError(response.get("message") or "Paystack could not verify this payment.")
    return response


def _paystack_request(path: str, *, method: str = "GET", payload: dict | None = None) -> dict:
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError("Paystack is not configured yet. Add PAYSTACK_SECRET_KEY to your environment.")

    url = f"{settings.PAYSTACK_API_BASE_URL.rstrip('/')}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Accept": "application/json",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, method=method.upper(), headers=headers)

    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        message = payload.get("message") or body or f"Paystack returned HTTP {exc.code}."
        raise PaystackError(message) from exc
    except URLError as exc:
        raise PaystackError("Unable to reach Paystack right now. Please try again.") from exc

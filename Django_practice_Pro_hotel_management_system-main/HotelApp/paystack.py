import json
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings


class PaystackError(Exception):
    pass


def paystack_is_configured(secret_key: Optional[str] = None) -> bool:
    return bool(secret_key or settings.PAYSTACK_SECRET_KEY)


def amount_to_subunit(amount: Decimal) -> int:
    decimal_amount = Decimal(str(amount))
    return int((decimal_amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def initialize_transaction(
    *,
    email: str,
    amount: Decimal,
    reference: str,
    callback_url: str,
    metadata: Optional[Dict[str, Any]] = None,
    first_name: str = "",
    last_name: str = "",
    secret_key: Optional[str] = None,
    currency: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "email": email,
        "amount": str(amount_to_subunit(amount)),
        "reference": reference,
        "callback_url": callback_url,
        "currency": currency or settings.PAYSTACK_CURRENCY,
        "metadata": metadata or {},
    }
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name

    response = _paystack_request(
        "/transaction/initialize",
        method="POST",
        payload=payload,
        secret_key=secret_key,
    )
    data = response.get("data") or {}
    if not response.get("status") or not data.get("authorization_url"):
        raise PaystackError(response.get("message") or "Paystack could not initialize this payment.")
    return data


def verify_transaction(reference: str, *, secret_key: Optional[str] = None) -> Dict[str, Any]:
    response = _paystack_request(
        f"/transaction/verify/{quote(reference)}",
        secret_key=secret_key,
    )
    if not response.get("status"):
        raise PaystackError(response.get("message") or "Paystack could not verify this payment.")
    return response


def _paystack_request(
    path: str,
    *,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    secret_key: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_secret_key = secret_key or settings.PAYSTACK_SECRET_KEY

    if not resolved_secret_key:
        raise PaystackError("Paystack is not configured yet. Add PAYSTACK_SECRET_KEY to your environment.")

    url = f"{settings.PAYSTACK_API_BASE_URL.rstrip('/')}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {resolved_secret_key}",
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
            error_payload = json.loads(body)
        except json.JSONDecodeError:
            error_payload = {}
        message = error_payload.get("message") or body or f"Paystack returned HTTP {exc.code}."
        raise PaystackError(message) from exc
    except URLError as exc:
        raise PaystackError("Unable to reach Paystack right now. Please try again.") from exc


class PaystackResponse:
    def __init__(self, status: bool, data: Optional[Dict[str, Any]] = None, raw: Optional[Dict[str, Any]] = None):
        self.status = status
        self.data = SimpleNamespace(**(data or {}))
        self.raw = raw or {"status": status, "data": data or {}}


class _TransactionsClient:
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key

    def initialize(self, *, email: str, amount: int, reference: str, callback_url: str) -> PaystackResponse:
        try:
            data = initialize_transaction(
                email=email,
                amount=(Decimal(str(amount)) / Decimal("100")),
                reference=reference,
                callback_url=callback_url,
                secret_key=self.secret_key,
            )
        except PaystackError as exc:
            return PaystackResponse(False, raw={"status": False, "message": str(exc)})
        return PaystackResponse(True, data=data, raw={"status": True, "data": data})

    def verify(self, *, reference: str) -> PaystackResponse:
        try:
            raw = verify_transaction(reference, secret_key=self.secret_key)
        except PaystackError as exc:
            return PaystackResponse(False, raw={"status": False, "message": str(exc)})
        return PaystackResponse(bool(raw.get("status")), data=raw.get("data") or {}, raw=raw)


class PaystackClient:
    def __init__(self, secret_key: Optional[str] = None):
        self.transactions = _TransactionsClient(secret_key=secret_key)

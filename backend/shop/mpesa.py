import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from os import environ as env

import requests
from django.core.cache import cache


def _setting(name, *aliases):
    for key in (name, *aliases):
        value = env.get(key)
        if value:
            return value
    raise KeyError(name)


def _callback_url():
    callback_url = _setting("MPESA_CALLBACK_URL", "MPESA_CALLBACK_BASE_URL").rstrip("/")
    if not callback_url.endswith("/api/mpesa/callback"):
        callback_url += "/api/mpesa/callback"
    callback_secret = env.get("MPESA_CALLBACK_SECRET", "").strip()
    return f"{callback_url}/{callback_secret}/" if callback_secret else f"{callback_url}/"


def round_kes_amount(amount_kes):
    try:
        amount = Decimal(amount_kes)
        if not amount.is_finite() or amount <= 0:
            raise InvalidOperation
    except (KeyError, InvalidOperation, ValueError):
        return None
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _base():
    if env.get("MPESA_ENV", "sandbox") == "sandbox":
        return "https://sandbox.safaricom.co.ke"
    return "https://api.safaricom.co.ke"


def _token():
    cached_token = cache.get("mpesa:access-token")
    if cached_token:
        return cached_token
    response = requests.get(
        f"{_base()}/oauth/v1/generate?grant_type=client_credentials",
        auth=(env["MPESA_CONSUMER_KEY"], env["MPESA_CONSUMER_SECRET"]),
        timeout=15,
    )
    response.raise_for_status()
    token_data = response.json()
    access_token = token_data["access_token"]
    expires_in = int(token_data.get("expires_in", 3600))
    cache.set("mpesa:access-token", access_token, timeout=max(30, expires_in - 60))
    return access_token


def _password():
    nairobi_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=3)))
    timestamp = nairobi_time.strftime("%Y%m%d%H%M%S")
    raw_password = f'{_setting("MPESA_SHORTCODE")}{_setting("MPESA_PASSKEY")}{timestamp}'
    password = base64.b64encode(raw_password.encode()).decode()
    return password, timestamp


def normalize(phone):
    digits = "".join(character for character in str(phone) if character.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        digits = "254" + digits[1:]
    elif (digits.startswith("7") or digits.startswith("1")) and len(digits) == 9:
        digits = "254" + digits
    if len(digits) != 12 or not digits.startswith(("2547", "2541")):
        raise ValueError("Enter a valid Kenyan M-PESA number.")
    return digits


def stk_push(phone, amount, reference):
    password, timestamp = _password()
    normalized_phone = normalize(phone)
    body = {
        "BusinessShortCode": _setting("MPESA_SHORTCODE"),
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": env.get("MPESA_TRANSACTION_TYPE", "CustomerBuyGoodsOnline"),
        "Amount": int(amount),
        "PartyA": normalized_phone,
        "PartyB": _setting("MPESA_PARTY_B", "MPESA_TILL", "MPESA_TILL_NUMBER"),
        "PhoneNumber": normalized_phone,
        "CallBackURL": _callback_url(),
        "AccountReference": reference,
        "TransactionDesc": "TUVA order",
    }
    response = requests.post(
        f"{_base()}/mpesa/stkpush/v1/processrequest",
        json=body,
        headers={"Authorization": f"Bearer {_token()}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def query(checkout_request_id):
    password, timestamp = _password()
    response = requests.post(
        f"{_base()}/mpesa/stkpushquery/v1/query",
        headers={"Authorization": f"Bearer {_token()}"},
        timeout=20,
        json={
            "BusinessShortCode": _setting("MPESA_SHORTCODE"),
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        },
    )
    response.raise_for_status()
    return response.json()

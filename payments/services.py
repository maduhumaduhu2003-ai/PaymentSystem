import logging
import re
from decimal import Decimal, InvalidOperation
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("payments")

# ClickPesa configuration
CLICKPESA_BASE_URL = getattr(settings, "CLICKPESA_BASE_URL", "https://api.clickpesa.com/third-parties")
TOKEN_CACHE_KEY = "clickpesa_token"
TOKEN_CACHE_TIMEOUT = getattr(settings, "CLICKPESA_TOKEN_CACHE_TIMEOUT", 600)

# ============================================================================
# PHONE NUMBER
# ============================================================================

def clean_phone(phone):
    return re.sub(r"[\s\-\(\)]", "", (phone or "").strip())


def validate_tanzania_phone(phone):
    phone = clean_phone(phone)
    return bool(re.fullmatch(r"^(0[67][0-9]{8}|255[67][0-9]{8}|\+255[67][0-9]{8})$", phone))


def normalize_tanzania_phone(phone):
    phone = clean_phone(phone)
    if not phone or not validate_tanzania_phone(phone):
        return None
    if phone.startswith("+255"):
        return phone[1:]
    if phone.startswith("0"):
        return f"255{phone[1:]}"
    return phone


# ============================================================================
# TOKEN 
# ============================================================================

def get_clickpesa_token():
    cached = cache.get(TOKEN_CACHE_KEY)
    if cached:
        return cached

    client_id = getattr(settings, "CLICKPESA_CLIENT_ID", None)
    api_key = getattr(settings, "CLICKPESA_API_KEY", None)
    if not client_id or not api_key:
        logger.error("ClickPesa credentials not configured")
        return None

    try:
        response = requests.post(
            f"{CLICKPESA_BASE_URL}/third-parties/generate-token",  
            headers={
                "client-id": client_id,
                "api-key": api_key,
                "Accept": "application/json"
            },
            timeout=(5, 15),
        )
        response.raise_for_status()
        data = response.json()
        
        # Check success field
        if not data.get("success"):
            error_msg = data.get("message") or "Unknown error"
            logger.error(f"ClickPesa error: {error_msg}")
            return None
            
        token = data.get("token")
        if not token:
            logger.error(f"No token in response: {data}")
            return None

        if not token.startswith("Bearer "):
            token = f"Bearer {token}"

        cache.set(TOKEN_CACHE_KEY, token, TOKEN_CACHE_TIMEOUT)
        return token

    except requests.Timeout:
        logger.error("ClickPesa token request timed out")
        return None
    except requests.RequestException as e:
        logger.error(f"ClickPesa token request failed: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response: {e.response.text[:200]}")
        return None
    except Exception:
        logger.exception("Unexpected error generating ClickPesa token")
        return None


def _headers(token):
    return {"Authorization": token, "Content-Type": "application/json", "Accept": "application/json"}


# ============================================================================
# USSD PUSH
# ============================================================================

def initiate_clickpesa_ussd_push(token, amount, order_reference, phone_number):
    phone = normalize_tanzania_phone(phone_number)
    if not phone:
        return {"success": False, "message": "Invalid phone number", "ambiguous": False}

    try:
        amount_decimal = Decimal(str(amount))
        if amount_decimal <= 0:
            return {"success": False, "message": "Invalid amount", "ambiguous": False}
    except (InvalidOperation, ValueError, TypeError):
        return {"success": False, "message": "Invalid amount", "ambiguous": False}

    payload = {
        "amount": str(amount_decimal),
        "currency": "TZS",
        "orderReference": order_reference,
        "phoneNumber": phone,
    }

    try:
        response = requests.post(
            f"{CLICKPESA_BASE_URL}/payments/initiate-ussd-push-request",
            headers=_headers(token),
            json=payload,
            timeout=(5, 30),
        )

        try:
            data = response.json()
        except ValueError:
            logger.error(f"Invalid JSON from ClickPesa: HTTP {response.status_code}")
            return {
                "success": False,
                "message": "Invalid gateway response",
                "ambiguous": response.status_code >= 500,
            }

        if response.status_code in (200, 201):
            return {
                "success": True,
                "message": "USSD Push initiated",
                "data": data,
                "transaction_id": data.get("id") or data.get("transactionId"),
                "ambiguous": False,
            }

        if response.status_code == 401:
            cache.delete(TOKEN_CACHE_KEY)
            return {"success": False, "message": "Authentication failed", "ambiguous": False}

        if response.status_code == 429:
            return {"success": False, "message": "Gateway busy, try again", "ambiguous": True}

        if 500 <= response.status_code <= 599:
            return {"success": False, "message": "Gateway temporarily unavailable", "ambiguous": True}

        error_msg = data.get("message") or data.get("error") or f"HTTP {response.status_code}"
        return {"success": False, "message": error_msg, "ambiguous": False, "data": data}

    except requests.Timeout:
        return {"success": False, "message": "Payment request is being processed", "ambiguous": True}
    except requests.ConnectionError:
        return {"success": False, "message": "Unable to contact gateway", "ambiguous": True}
    except requests.RequestException as e:
        logger.error(f"ClickPesa request failed: {e}")
        return {"success": False, "message": "Gateway connection error", "ambiguous": True}


# ============================================================================
# PAYMENT QUERY
# ============================================================================

def query_clickpesa_payment(token, order_reference):
    if not order_reference:
        return {"success": False, "message": "Missing reference", "ambiguous": False}

    try:
        response = requests.get(
            f"{CLICKPESA_BASE_URL}/payments/{order_reference}",
            headers=_headers(token),
            timeout=(5, 30),
        )

        if response.status_code == 200:
            try:
                data = response.json()
                return {"success": True, "data": data, "ambiguous": False}
            except ValueError:
                return {"success": False, "message": "Invalid response", "ambiguous": True}

        if response.status_code == 404:
            return {"success": False, "message": "Payment not found", "ambiguous": False}

        if response.status_code == 401:
            cache.delete(TOKEN_CACHE_KEY)
            return {"success": False, "message": "Authentication failed", "ambiguous": True}

        if response.status_code == 429:
            return {"success": False, "message": "Rate limited", "ambiguous": True}

        if 500 <= response.status_code <= 599:
            return {"success": False, "message": "Gateway unavailable", "ambiguous": True}

        return {"success": False, "message": f"HTTP {response.status_code}", "ambiguous": False}

    except requests.Timeout:
        return {"success": False, "message": "Query timed out", "ambiguous": True}
    except requests.ConnectionError:
        return {"success": False, "message": "Connection error", "ambiguous": True}
    except requests.RequestException as e:
        logger.error(f"Query failed: {e}")
        return {"success": False, "message": "Query error", "ambiguous": True}


# ============================================================================
# GATEWAY DATA HELPERS
# ============================================================================

def extract_gateway_record(data):
    if isinstance(data, dict):
        nested = data.get("data")
        if isinstance(nested, dict):
            return nested
        if isinstance(nested, list) and nested and isinstance(nested[0], dict):
            return nested[0]
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return None


def get_gateway_status(data):
    return str(data.get("status") or data.get("paymentStatus") or "").upper() if isinstance(data, dict) else ""


def get_gateway_transaction_id(data):
    return data.get("id") or data.get("transactionId") if isinstance(data, dict) else None


def get_gateway_amount(data):
    if not isinstance(data, dict):
        return None
    value = data.get("collectedAmount") or data.get("amount")
    try:
        return Decimal(str(value)) if value is not None else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def get_gateway_currency(data):
    if not isinstance(data, dict):
        return None
    value = data.get("collectedCurrency") or data.get("currency")
    return str(value).upper().strip() if value else None


def classify_gateway_status(status):
    status = (status or "").upper().strip()
    if status in ("SUCCESS", "SETTLED", "COMPLETED"):
        return "PAID"
    if status in ("FAILED", "FAILURE", "DECLINED", "REJECTED", "ERROR"):
        return "FAILED"
    if status in ("PENDING", "PROCESSING"):
        return "PROCESSING"
    return None
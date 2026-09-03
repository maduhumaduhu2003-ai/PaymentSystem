import re
import requests
from django.conf import settings

# ============================================================================
# CLICKPESA BASE URL
# ============================================================================

CLICKPESA_BASE_URL = "https://api.clickpesa.com/third-parties"

# ============================================================================
# PHONE VALIDATION
# ============================================================================

def validate_tanzania_phone(phone: str) -> bool:
    phone = (phone or "").strip()
    phone = re.sub(r"[\s\-\(\)]", "", phone)
    pattern = r"^(0[67][0-9]{8}|255[67][0-9]{8}|\+255[67][0-9]{8})$"
    return bool(re.match(pattern, phone))

# ============================================================================
# CLICKPESA TOKEN
# ============================================================================

def get_clickpesa_token():
    url = f"{CLICKPESA_BASE_URL}/generate-token"
    headers = {
        "client-id": settings.CLICKPESA_CLIENT_ID,
        "api-key": settings.CLICKPESA_API_KEY,
    }

    try:
        response = requests.post(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None

        data = response.json()
        token = data.get("token")

        if not token:
            return None

        if not token.startswith("Bearer "):
            token = f"Bearer {token}"

        return token

    except:
        return None

# ============================================================================
# COMMON HEADERS
# ============================================================================

def clickpesa_headers(token):
    return {
        "Authorization": token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

# ============================================================================
# PREVIEW USSD PUSH
# ============================================================================

def preview_clickpesa_ussd_push(token, amount, order_reference, phone_number, fetch_sender_details=False):
    url = f"{CLICKPESA_BASE_URL}/payments/preview-ussd-push-request"
    payload = {
        "amount": str(amount),
        "currency": "TZS",
        "orderReference": order_reference,
        "phoneNumber": phone_number,
        "fetchSenderDetails": fetch_sender_details,
    }

    try:
        response = requests.post(url, headers=clickpesa_headers(token), json=payload, timeout=30)

        try:
            data = response.json()
        except:
            data = {"raw": response.text}

        if response.status_code == 200:
            return {
                "success": True,
                **(data if isinstance(data, dict) else {"data": data})
            }

        message = data.get("message") if isinstance(data, dict) else None
        if not message:
            message = f"ClickPesa preview failed (HTTP {response.status_code})"

        return {
            "success": False,
            "status_code": response.status_code,
            "message": message,
            "data": data,
        }

    except:
        return {
            "success": False,
            "message": "Unable to connect to ClickPesa.",
        }

# ============================================================================
# INITIATE USSD PUSH
# ============================================================================

def initiate_clickpesa_ussd_push(token, amount, order_reference, phone_number):
    url = f"{CLICKPESA_BASE_URL}/payments/initiate-ussd-push-request"
    payload = {
        "amount": str(amount),
        "currency": "TZS",
        "orderReference": order_reference,
        "phoneNumber": phone_number,
    }

    try:
        response = requests.post(url, headers=clickpesa_headers(token), json=payload, timeout=30)

        try:
            data = response.json()
        except:
            data = {"raw": response.text}

        if response.status_code in [200, 201]:
            return {
                "success": True,
                **(data if isinstance(data, dict) else {"data": data})
            }

        message = data.get("message") if isinstance(data, dict) else None
        if not message:
            message = f"ClickPesa payment initiation failed (HTTP {response.status_code})"

        return {
            "success": False,
            "status_code": response.status_code,
            "message": message,
            "data": data,
        }

    except:
        return {
            "success": False,
            "message": "Unable to connect to ClickPesa.",
        }

# ============================================================================
# QUERY PAYMENT STATUS
# ============================================================================

def query_clickpesa_payment(token, order_reference):
    url = f"{CLICKPESA_BASE_URL}/payments/{order_reference}"

    try:
        response = requests.get(url, headers=clickpesa_headers(token), timeout=30)

        try:
            data = response.json()
        except:
            data = {"raw": response.text}

        if response.status_code == 200:
            return {
                "success": True,
                "data": data,
            }

        message = data.get("message") if isinstance(data, dict) else None
        if not message:
            message = f"Unable to query ClickPesa payment (HTTP {response.status_code})"

        return {
            "success": False,
            "status_code": response.status_code,
            "message": message,
            "data": data,
        }

    except:
        return {
            "success": False,
            "message": "Unable to connect to ClickPesa.",
        }
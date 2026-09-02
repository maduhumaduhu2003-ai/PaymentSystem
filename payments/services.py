import re
import requests
from django.conf import settings

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
    url = "https://api.clickpesa.com/third-parties/generate-token"
    
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
        
        # Token inarudi tayari na "Bearer"
        if token and not token.startswith("Bearer "):
            return f"Bearer {token}"
        
        return token
        
    except:
        return None
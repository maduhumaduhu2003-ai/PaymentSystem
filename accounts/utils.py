import re


def validate_tanzania_phone(phone: str) -> bool:
    """
    Validate Tanzania phone number format.
    Supports: 07XXXXXXXX, 2557XXXXXXXX, +2557XXXXXXXX
    """
    if not phone:
        return False
    
    phone = phone.strip()
    
    # Remove spaces, dashes, parentheses
    phone = re.sub(r"[\s\-\(\)]", "", phone)
    
    # Pattern for Tanzania phone numbers
    # 07XXXXXXXX, 2557XXXXXXXX, +2557XXXXXXXX
    pattern = r"^(0[67][0-9]{8}|255[67][0-9]{8}|\+255[67][0-9]{8})$"
    
    return bool(re.match(pattern, phone))


def normalize_phone(phone):
    """
    Normalize Tanzania phone number to 255XXXXXXXX format.
    
    Examples:
    0712345678 -> 255712345678
    255712345678 -> 255712345678
    +255712345678 -> 255712345678
    """
    if not phone:
        return None
    
    phone = phone.strip()
    
    # Remove spaces, dashes, parentheses
    phone = re.sub(r"[\s\-\(\)]", "", phone)
    
    if phone.startswith('0'):
        return "255" + phone[-9:]
    
    if phone.startswith('+255'):
        return phone.replace("+", "")
    
    if phone.startswith('255'):
        return phone
    
    return None
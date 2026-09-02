# accounts/utils.py
def normalize_phone(phone):
    phone = phone.strip()

    if phone.startswith('0'):
        return "255" + phone[-9:]
    if phone.startswith('+255'):
        return phone.replace("+", "")

    if phone.startswith('255'):
        return phone

    return None
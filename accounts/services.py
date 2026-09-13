# accounts/services.py - Unda file hii

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone_number, message):
    """
    Send SMS via Beem Africa or other provider.
    
    Replace with your actual SMS provider.
    """
    try:
        # =========================================================
        # OPTION 1: Beem Africa
        # =========================================================
        # import requests
        # 
        # url = "https://apisms.beem.africa/v1/send"
        # 
        # payload = {
        #     "source_addr": "SATPAY",
        #     "schedule_time": "",
        #     "encoding": 0,
        #     "message": message,
        #     "recipients": [
        #         {
        #             "recipient_id": 1,
        #             "dest_addr": phone_number
        #         }
        #     ]
        # }
        # 
        # headers = {
        #     'Content-Type': 'application/json',
        #     'Authorization': f'Basic {settings.BEEM_API_KEY}',
        # }
        # 
        # response = requests.post(url, json=payload, headers=headers)
        # return response.status_code == 200
        
        # =========================================================
        # OPTION 2: NextSMS
        # =========================================================
        # import requests
        # 
        # url = "https://messaging-service.co.tz/api/sms/v1/text/single"
        # 
        # payload = {
        #     "from": "SATPAY",
        #     "to": phone_number,
        #     "text": message,
        # }
        # 
        # headers = {
        #     'Content-Type': 'application/json',
        #     'Authorization': f'Basic {settings.NEXTSMS_API_KEY}',
        # }
        # 
        # response = requests.post(url, json=payload, headers=headers)
        # return response.status_code == 200
        
        # =========================================================
        # DEVELOPMENT: Just log the SMS
        # =========================================================
        logger.info(f"📱 SMS to {phone_number}: {message}")
        print(f"📱 SMS to {phone_number}: {message}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False


def send_password_reset_otp(phone_number, otp_code):
    """Send password reset OTP via SMS"""
    message = f"Your SATPAY password reset code is: {otp_code}. Valid for 10 minutes. Do not share this code."
    return send_sms(phone_number, message)
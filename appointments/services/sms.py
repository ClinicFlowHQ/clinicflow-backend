# -*- coding: utf-8 -*-
"""
SMS sending service using Africa's Talking.

Production-hardened:
- Initialize SDK once (not per call)
- Normalize DRC phone numbers to E.164 (+243...)
- Mask phone numbers in log output
- Return structured result dict with message_id
- Timeout protection via SDK (or fallback signal)
- Forces UTF-8 encoding for French accented characters
"""

import logging
import re

import requests as http_requests

from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phone number helpers
# ---------------------------------------------------------------------------
_DIGITS_ONLY = re.compile(r"[^\d+]")
_E164_PATTERN = re.compile(r"^\+\d{8,15}$")

# DRC country code
DRC_COUNTRY_CODE = "+243"


def normalize_phone_drc(raw: str) -> str | None:
    """
    Normalize a DRC phone number to E.164 format (+243XXXXXXXXX).

    Accepts:
        "0812345678"    -> "+243812345678"
        "812345678"     -> "+243812345678"
        "+243812345678" -> "+243812345678"
        "243812345678"  -> "+243812345678"

    Returns None if the result does not match E.164.
    """
    if not raw:
        return None

    phone = _DIGITS_ONLY.sub("", raw.strip())

    # Already has +243 prefix
    if phone.startswith("+243"):
        pass
    # Has 243 prefix without +
    elif phone.startswith("243") and len(phone) >= 12:
        phone = "+" + phone
    # Local format starting with 0
    elif phone.startswith("0") and len(phone) >= 9:
        phone = DRC_COUNTRY_CODE + phone[1:]
    # Bare local number (no leading 0)
    elif len(phone) >= 9 and not phone.startswith("+"):
        phone = DRC_COUNTRY_CODE + phone
    # Ensure leading +
    if not phone.startswith("+"):
        phone = "+" + phone

    if _E164_PATTERN.match(phone):
        return phone
    return None


def mask_phone(phone: str) -> str:
    """
    Mask a phone number for safe logging.
    "+243812345678" -> "+2438*****678"
    """
    if not phone or len(phone) <= 7:
        return "***"
    return phone[:5] + "*" * (len(phone) - 8) + phone[-3:]


# ---------------------------------------------------------------------------
# Main send function
# ---------------------------------------------------------------------------
def send_sms(phone_number: str, message: str) -> dict:
    """
    Send an SMS via Africa's Talking.

    Args:
        phone_number: Recipient phone (raw or E.164). Will be normalised.
        message: SMS body.

    Returns:
        {
            "ok": bool,
            "provider": "africastalking",
            "message_id": str | None,
            "error": str | None,
            "phone_normalised": str | None,
        }
    """
    result = {
        "ok": False,
        "provider": "africastalking",
        "message_id": None,
        "error": None,
        "phone_normalised": None,
    }

    # --- Normalise phone ---
    normalised = normalize_phone_drc(phone_number)
    if not normalised:
        result["error"] = f"Invalid phone number: {mask_phone(phone_number)}"
        logger.warning("SMS skipped — invalid phone: %s", mask_phone(phone_number))
        return result

    result["phone_normalised"] = normalised
    masked = mask_phone(normalised)

    # --- Build request (direct HTTP POST for UTF-8 control) ---
    # The AT Python SDK does not expose a Unicode/encoding parameter.
    # Sending via requests directly with explicit UTF-8 Content-Type
    # ensures accented French characters (é, è, à, ô …) are preserved.
    username = settings.AFRICASTALKING_USERNAME
    api_key = settings.AFRICASTALKING_API_KEY
    sender_id = settings.AFRICASTALKING_SENDER_ID

    if not username or not api_key:
        result["error"] = "SMS provider not configured"
        logger.error("Africa's Talking credentials not configured")
        return result

    is_sandbox = (username == "sandbox")
    api_url = (
        "https://api.sandbox.africastalking.com/version1/messaging"
        if is_sandbox
        else "https://api.africastalking.com/version1/messaging"
    )

    payload = {
        "username": username,
        "to": normalised,
        "message": message,
        "bulkSMSMode": 1,
    }
    if sender_id:
        payload["from"] = sender_id

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "apiKey": api_key,
    }

    # --- Send with timeout guard ---
    try:
        # Pass payload as dict — requests.post encodes it via
        # urllib.parse.urlencode which uses UTF-8 for non-ASCII chars.
        # Combined with charset=UTF-8 in Content-Type, this ensures
        # accented characters (é, è, à, ô …) are transmitted correctly.
        resp = http_requests.post(
            api_url,
            data=payload,
            headers=headers,
            timeout=30,
        )

        # Handle non-2xx responses
        if resp.status_code >= 400:
            snippet = resp.text[:200] if resp.text else "(empty)"
            result["error"] = f"HTTP {resp.status_code}: {snippet}"
            logger.warning("SMS HTTP error for %s: %s %s", masked, resp.status_code, snippet)
            return result

        # Parse JSON safely
        try:
            response = resp.json()
        except (ValueError, TypeError):
            snippet = resp.text[:200] if resp.text else "(empty)"
            result["error"] = f"Invalid JSON from provider: {snippet}"
            logger.warning("SMS non-JSON response for %s: %s", masked, snippet)
            return result

        # Africa's Talking response:
        # {"SMSMessageData": {"Recipients": [{"status": "Success", "messageId": "...", ...}]}}
        recipients = response.get("SMSMessageData", {}).get("Recipients", [])

        if recipients:
            status = recipients[0].get("status", "Unknown")
            msg_id = recipients[0].get("messageId")

            if status == "Success":
                result["ok"] = True
                result["message_id"] = msg_id
                logger.info("SMS sent to %s  [msg_id=%s]", masked, msg_id)
            else:
                result["error"] = f"Provider status: {status}"
                logger.warning("SMS failed for %s: %s", masked, status)
        else:
            result["error"] = "No recipients in provider response"
            logger.warning("SMS failed for %s: empty recipients in response", masked)

    except Exception as exc:
        result["error"] = str(exc)[:200]
        logger.error("SMS send error for %s: %s", masked, exc)

    return result

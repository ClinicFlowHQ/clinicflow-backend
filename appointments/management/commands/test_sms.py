"""
Management command to send a test SMS for end-to-end verification.

Usage:
    python manage.py test_sms +243812345678
    python manage.py test_sms +243812345678 --message "Custom test message"

Returns exit code 1 on failure so CI/CD or manual checks can detect problems.
"""

import sys

from django.conf import settings
from django.core.management.base import BaseCommand

from appointments.services.sms import mask_phone, send_sms


class Command(BaseCommand):
    help = "Send a test SMS to verify Africa's Talking configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "phone",
            help='Phone number (E.164 or local DRC format, e.g. +243812345678 or 0812345678)',
        )
        parser.add_argument(
            "--message",
            default="Test SMS from ClinicFlow. Si vous recevez ce message, la configuration est correcte.",
            help="Custom message text",
        )

    def handle(self, *args, **options):
        phone = options["phone"]
        message = options["message"]
        masked = mask_phone(phone)

        self.stdout.write(f"Africa's Talking username: {settings.AFRICASTALKING_USERNAME or '(not set)'}")
        self.stdout.write(f"Sender ID: {settings.AFRICASTALKING_SENDER_ID or '(default/shared)'}")
        self.stdout.write(f"Sending test SMS to {masked}...")
        self.stdout.write("")

        result = send_sms(phone, message)

        if result["ok"]:
            self.stdout.write(self.style.SUCCESS("SMS sent successfully."))
            self.stdout.write(f"  Provider:   {result['provider']}")
            self.stdout.write(f"  Message ID: {result['message_id']}")
            self.stdout.write(f"  Phone used: {mask_phone(result.get('phone_normalised', ''))}")
        else:
            self.stdout.write(self.style.ERROR("SMS send FAILED."))
            self.stdout.write(f"  Error: {result['error']}")
            self.stdout.write("")
            self.stdout.write("Troubleshooting:")
            self.stdout.write("  1. Check AFRICASTALKING_USERNAME and AFRICASTALKING_API_KEY env vars")
            self.stdout.write("  2. Verify phone number format (must be valid DRC number)")
            self.stdout.write("  3. Check Africa's Talking dashboard for account balance")
            sys.exit(1)

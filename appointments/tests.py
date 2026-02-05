"""
Tests for the SMS reminder system.

Covers:
- Phone number normalisation (DRC E.164)
- Phone masking for logs
- send_sms structured result on invalid phone (no SDK needed)
- Reminder query selects correct statuses (CONFIRMED, RESCHEDULED only)
- Cutoff rule: before 17:00, exactly 17:00, appointment day, after appointment
- Management command end-to-end: success logging, failure logging, missing phone
"""

from datetime import datetime, time, timedelta, timezone as dt_timezone
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from appointments.management.commands.send_appointment_reminders import (
    build_sms_message,
    format_date_french,
    is_eligible_for_send,
    ELIGIBLE_STATUSES,
)
from appointments.models import Appointment, AppointmentSMSLog
from appointments.services.sms import mask_phone, normalize_phone_drc, send_sms
from patients.models import Patient

User = get_user_model()

CLINIC_TZ = ZoneInfo("Africa/Kinshasa")


# =========================================================================
# Phone normalisation
# =========================================================================
class NormalizePhoneDRCTest(TestCase):
    """Test DRC phone number normalisation to E.164."""

    def test_local_with_leading_zero(self):
        self.assertEqual(normalize_phone_drc("0812345678"), "+243812345678")

    def test_local_without_leading_zero(self):
        self.assertEqual(normalize_phone_drc("812345678"), "+243812345678")

    def test_already_e164(self):
        self.assertEqual(normalize_phone_drc("+243812345678"), "+243812345678")

    def test_with_country_code_no_plus(self):
        self.assertEqual(normalize_phone_drc("243812345678"), "+243812345678")

    def test_with_spaces_and_dashes(self):
        self.assertEqual(normalize_phone_drc("+243 81-234-5678"), "+243812345678")

    def test_empty_string(self):
        self.assertIsNone(normalize_phone_drc(""))

    def test_none_input(self):
        self.assertIsNone(normalize_phone_drc(None))

    def test_too_short(self):
        self.assertIsNone(normalize_phone_drc("123"))

    def test_garbage_input(self):
        self.assertIsNone(normalize_phone_drc("abcdefg"))


# =========================================================================
# Phone masking
# =========================================================================
class MaskPhoneTest(TestCase):
    """Test phone number masking for safe logging."""

    def test_standard_mask(self):
        masked = mask_phone("+243812345678")
        self.assertNotIn("812345678", masked)
        self.assertTrue(masked.startswith("+2438"))
        self.assertTrue(masked.endswith("678"))

    def test_short_number_fully_masked(self):
        self.assertEqual(mask_phone("12345"), "***")

    def test_empty(self):
        self.assertEqual(mask_phone(""), "***")


# =========================================================================
# send_sms structured result on invalid phone
# =========================================================================
class SendSmsInvalidPhoneTest(TestCase):
    """send_sms should return ok=False without calling the provider for bad numbers."""

    def test_invalid_phone_returns_error(self):
        result = send_sms("invalid", "Hello")
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["error"])
        self.assertIsNone(result["message_id"])
        self.assertEqual(result["provider"], "africastalking")

    def test_empty_phone_returns_error(self):
        result = send_sms("", "Hello")
        self.assertFalse(result["ok"])
        self.assertIn("Invalid", result["error"])


# =========================================================================
# French date formatting
# =========================================================================
class FormatDateFrenchTest(TestCase):
    """Test French date formatting with full month names."""

    def test_february(self):
        dt = datetime(2026, 2, 3, 10, 0)
        self.assertEqual(format_date_french(dt), "3 février 2026")

    def test_december(self):
        dt = datetime(2026, 12, 25, 14, 0)
        self.assertEqual(format_date_french(dt), "25 décembre 2026")

    def test_january_first(self):
        dt = datetime(2026, 1, 1, 8, 0)
        self.assertEqual(format_date_french(dt), "1 janvier 2026")


# =========================================================================
# SMS message builder
# =========================================================================
class BuildSmsMessageTest(TestCase):
    """Test the personalised French SMS message builder."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="doc_msg", password="testpass123")
        cls.patient = Patient.objects.create(
            first_name="Marie",
            last_name="Kabila",
            sex="F",
            date_of_birth="2015-06-15",
            phone="+243812345678",
            address="Kinshasa",
            created_by=cls.user,
        )

    @patch("appointments.management.commands.send_appointment_reminders.timezone.now")
    def test_bonjour_before_18h(self, mock_now):
        # 17:00 Kinshasa -> should use "Bonjour"
        mock_now.return_value = datetime(2026, 2, 2, 16, 0, tzinfo=dt_timezone.utc)  # 17:00 Kinshasa
        scheduled = datetime(2026, 2, 3, 9, 0, tzinfo=CLINIC_TZ)
        msg = build_sms_message(self.patient, scheduled)
        self.assertIn("Bonjour Marie Kabila", msg)
        self.assertIn("09:00", msg)
        self.assertIn("3 février 2026", msg)
        self.assertIn("Dr Mukwamu B. Justin", msg)

    @patch("appointments.management.commands.send_appointment_reminders.timezone.now")
    def test_bonsoir_after_18h(self, mock_now):
        # 19:00 Kinshasa -> should use "Bonsoir"
        mock_now.return_value = datetime(2026, 2, 2, 18, 0, tzinfo=dt_timezone.utc)  # 19:00 Kinshasa
        scheduled = datetime(2026, 2, 3, 14, 0, tzinfo=CLINIC_TZ)
        msg = build_sms_message(self.patient, scheduled)
        self.assertIn("Bonsoir Marie Kabila", msg)


# =========================================================================
# Eligible statuses
# =========================================================================
class EligibleStatusesTest(TestCase):
    """Verify that only CONFIRMED and RESCHEDULED are eligible."""

    def test_eligible_list(self):
        self.assertEqual(ELIGIBLE_STATUSES, ["CONFIRMED", "RESCHEDULED"])

    def test_scheduled_not_eligible(self):
        self.assertNotIn("SCHEDULED", ELIGIBLE_STATUSES)

    def test_cancelled_not_eligible(self):
        self.assertNotIn("CANCELLED", ELIGIBLE_STATUSES)

    def test_completed_not_eligible(self):
        self.assertNotIn("COMPLETED", ELIGIBLE_STATUSES)

    def test_no_show_not_eligible(self):
        self.assertNotIn("NO_SHOW", ELIGIBLE_STATUSES)


# =========================================================================
# Cutoff rule (is_eligible_for_send)
# =========================================================================
@override_settings(CLINIC_TIMEZONE="Africa/Kinshasa")
class CutoffRuleTest(TestCase):
    """Test the strict cutoff logic for sending reminders."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="doc_cutoff", password="testpass123")
        cls.patient = Patient.objects.create(
            first_name="Pierre",
            last_name="Lumumba",
            sex="M",
            date_of_birth="2010-03-10",
            phone="+243812345678",
            address="Kinshasa",
            created_by=cls.user,
        )

    def _make_appointment(self, scheduled_at, **kwargs):
        defaults = {
            "patient": self.patient,
            "doctor": self.user,
            "scheduled_at": scheduled_at,
            "status": "CONFIRMED",
            "reminders_enabled": True,
        }
        defaults.update(kwargs)
        return Appointment.objects.create(**defaults)

    def test_before_17h_cutoff_not_eligible(self):
        """At 16:59 the day before -> not yet eligible."""
        appt_time = datetime(2026, 2, 4, 10, 0, tzinfo=CLINIC_TZ)  # appointment Feb 4 at 10:00
        appt = self._make_appointment(scheduled_at=appt_time)
        now = datetime(2026, 2, 3, 16, 59, tzinfo=CLINIC_TZ)  # Feb 3 at 16:59

        eligible, reason = is_eligible_for_send(appt, now, CLINIC_TZ)
        self.assertFalse(eligible)
        self.assertIn("before cutoff", reason)

    def test_exactly_17h_cutoff_eligible(self):
        """At exactly 17:00 the day before -> eligible."""
        appt_time = datetime(2026, 2, 4, 10, 0, tzinfo=CLINIC_TZ)
        appt = self._make_appointment(scheduled_at=appt_time)
        now = datetime(2026, 2, 3, 17, 0, tzinfo=CLINIC_TZ)

        eligible, reason = is_eligible_for_send(appt, now, CLINIC_TZ)
        self.assertTrue(eligible)
        self.assertEqual(reason, "eligible")

    def test_at_2300_day_before_eligible(self):
        """At 23:00 the day before -> still eligible."""
        appt_time = datetime(2026, 2, 4, 10, 0, tzinfo=CLINIC_TZ)
        appt = self._make_appointment(scheduled_at=appt_time)
        now = datetime(2026, 2, 3, 23, 0, tzinfo=CLINIC_TZ)

        eligible, reason = is_eligible_for_send(appt, now, CLINIC_TZ)
        self.assertTrue(eligible)

    def test_appointment_day_morning_not_eligible(self):
        """On the appointment day itself (even early morning) -> missed window."""
        appt_time = datetime(2026, 2, 4, 10, 0, tzinfo=CLINIC_TZ)
        appt = self._make_appointment(scheduled_at=appt_time)
        now = datetime(2026, 2, 4, 7, 0, tzinfo=CLINIC_TZ)  # appointment day, 07:00

        eligible, reason = is_eligible_for_send(appt, now, CLINIC_TZ)
        self.assertFalse(eligible)
        self.assertIn("appointment day", reason)

    def test_after_appointment_time_not_eligible(self):
        """After the appointment time has passed -> not eligible."""
        appt_time = datetime(2026, 2, 4, 10, 0, tzinfo=CLINIC_TZ)
        appt = self._make_appointment(scheduled_at=appt_time)
        now = datetime(2026, 2, 4, 11, 0, tzinfo=CLINIC_TZ)

        eligible, reason = is_eligible_for_send(appt, now, CLINIC_TZ)
        self.assertFalse(eligible)

    def test_two_days_before_not_eligible(self):
        """Two days before the appointment -> not the day before."""
        appt_time = datetime(2026, 2, 5, 10, 0, tzinfo=CLINIC_TZ)
        appt = self._make_appointment(scheduled_at=appt_time)
        now = datetime(2026, 2, 3, 17, 30, tzinfo=CLINIC_TZ)  # 2 days before

        eligible, reason = is_eligible_for_send(appt, now, CLINIC_TZ)
        self.assertFalse(eligible)
        self.assertIn("not the day before", reason)


# =========================================================================
# Reminder query (updated for CONFIRMED/RESCHEDULED)
# =========================================================================
@override_settings(CLINIC_TIMEZONE="Africa/Kinshasa")
class ReminderQueryTest(TestCase):
    """Test that the reminder DB query selects the correct appointments."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testdoc", password="testpass123")
        cls.patient = Patient.objects.create(
            first_name="Jean",
            last_name="Dupont",
            sex="M",
            date_of_birth="2000-01-01",
            phone="+243812345678",
            address="Kinshasa",
            created_by=cls.user,
        )

    def _create_appointment(self, scheduled_at, **kwargs):
        defaults = {
            "patient": self.patient,
            "doctor": self.user,
            "scheduled_at": scheduled_at,
            "status": "CONFIRMED",
            "reminders_enabled": True,
        }
        defaults.update(kwargs)
        return Appointment.objects.create(**defaults)

    def _query_candidates(self, tomorrow):
        """Reproduce the query from the management command."""
        tomorrow_start = datetime.combine(tomorrow, time.min, tzinfo=CLINIC_TZ)
        day_after = tomorrow + timedelta(days=1)
        tomorrow_end = datetime.combine(day_after, time.max, tzinfo=CLINIC_TZ)
        start_utc = tomorrow_start.astimezone(dt_timezone.utc)
        end_utc = tomorrow_end.astimezone(dt_timezone.utc)

        return Appointment.objects.filter(
            scheduled_at__gte=start_utc,
            scheduled_at__lt=end_utc,
            status__in=ELIGIBLE_STATUSES,
            reminders_enabled=True,
            reminder_sent_at__isnull=True,
        )

    def test_confirmed_included(self):
        """A CONFIRMED appointment for tomorrow should be found."""
        tomorrow = timezone.now().astimezone(CLINIC_TZ).date() + timedelta(days=1)
        scheduled = datetime.combine(tomorrow, time(10, 0), tzinfo=CLINIC_TZ)
        appt = self._create_appointment(scheduled_at=scheduled, status="CONFIRMED")
        self.assertIn(appt, self._query_candidates(tomorrow))

    def test_rescheduled_included(self):
        """A RESCHEDULED appointment for tomorrow should be found."""
        tomorrow = timezone.now().astimezone(CLINIC_TZ).date() + timedelta(days=1)
        scheduled = datetime.combine(tomorrow, time(10, 0), tzinfo=CLINIC_TZ)
        appt = self._create_appointment(scheduled_at=scheduled, status="RESCHEDULED")
        self.assertIn(appt, self._query_candidates(tomorrow))

    def test_scheduled_excluded(self):
        """A SCHEDULED (unconfirmed) appointment should NOT be found."""
        tomorrow = timezone.now().astimezone(CLINIC_TZ).date() + timedelta(days=1)
        scheduled = datetime.combine(tomorrow, time(10, 0), tzinfo=CLINIC_TZ)
        appt = self._create_appointment(scheduled_at=scheduled, status="SCHEDULED")
        self.assertNotIn(appt, self._query_candidates(tomorrow))

    def test_cancelled_excluded(self):
        """A CANCELLED appointment should NOT be found."""
        tomorrow = timezone.now().astimezone(CLINIC_TZ).date() + timedelta(days=1)
        scheduled = datetime.combine(tomorrow, time(10, 0), tzinfo=CLINIC_TZ)
        appt = self._create_appointment(scheduled_at=scheduled, status="CANCELLED")
        self.assertNotIn(appt, self._query_candidates(tomorrow))

    def test_completed_excluded(self):
        """A COMPLETED appointment should NOT be found."""
        tomorrow = timezone.now().astimezone(CLINIC_TZ).date() + timedelta(days=1)
        scheduled = datetime.combine(tomorrow, time(10, 0), tzinfo=CLINIC_TZ)
        appt = self._create_appointment(scheduled_at=scheduled, status="COMPLETED")
        self.assertNotIn(appt, self._query_candidates(tomorrow))

    def test_no_show_excluded(self):
        """A NO_SHOW appointment should NOT be found."""
        tomorrow = timezone.now().astimezone(CLINIC_TZ).date() + timedelta(days=1)
        scheduled = datetime.combine(tomorrow, time(10, 0), tzinfo=CLINIC_TZ)
        appt = self._create_appointment(scheduled_at=scheduled, status="NO_SHOW")
        self.assertNotIn(appt, self._query_candidates(tomorrow))

    def test_already_sent_excluded(self):
        """Appointments with reminder_sent_at set should be excluded."""
        tomorrow = timezone.now().astimezone(CLINIC_TZ).date() + timedelta(days=1)
        scheduled = datetime.combine(tomorrow, time(10, 0), tzinfo=CLINIC_TZ)
        appt = self._create_appointment(
            scheduled_at=scheduled,
            reminder_sent_at=timezone.now(),
        )
        self.assertNotIn(appt, self._query_candidates(tomorrow))

    def test_reminders_disabled_excluded(self):
        """Appointments with reminders_enabled=False should be excluded."""
        tomorrow = timezone.now().astimezone(CLINIC_TZ).date() + timedelta(days=1)
        scheduled = datetime.combine(tomorrow, time(10, 0), tzinfo=CLINIC_TZ)
        appt = self._create_appointment(
            scheduled_at=scheduled,
            reminders_enabled=False,
        )
        self.assertNotIn(appt, self._query_candidates(tomorrow))


# =========================================================================
# Management command end-to-end
# =========================================================================
@override_settings(CLINIC_TIMEZONE="Africa/Kinshasa", SMS_MAX_REMINDERS_PER_RUN=200)
class SendReminderCommandTest(TestCase):
    """End-to-end test of the send_appointment_reminders management command."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="doc_cmd", password="testpass123")
        cls.patient = Patient.objects.create(
            first_name="Alice",
            last_name="Mwamba",
            sex="F",
            date_of_birth="2018-04-20",
            phone="+243812345678",
            address="Kinshasa",
            created_by=cls.user,
        )
        cls.patient_no_phone = Patient.objects.create(
            first_name="Bob",
            last_name="Nzuzi",
            sex="M",
            date_of_birth="2019-07-10",
            phone="",
            address="Kinshasa",
            created_by=cls.user,
        )

    def _make_appointment(self, patient, scheduled_at, **kwargs):
        defaults = {
            "patient": patient,
            "doctor": self.user,
            "scheduled_at": scheduled_at,
            "status": "CONFIRMED",
            "reminders_enabled": True,
        }
        defaults.update(kwargs)
        return Appointment.objects.create(**defaults)

    @patch("appointments.management.commands.send_appointment_reminders.send_sms")
    @patch("appointments.management.commands.send_appointment_reminders.timezone.now")
    def test_success_sets_reminder_sent_and_logs(self, mock_now, mock_send):
        """Successful send: reminder_sent_at is set, SUCCESS log created."""
        # Fix "now" to Feb 3, 2026 at 17:00 Kinshasa (16:00 UTC)
        fake_now = datetime(2026, 2, 3, 16, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = fake_now

        # Appointment tomorrow Feb 4 at 10:00 Kinshasa
        scheduled = datetime(2026, 2, 4, 10, 0, tzinfo=CLINIC_TZ)
        appt = self._make_appointment(self.patient, scheduled_at=scheduled)

        mock_send.return_value = {
            "ok": True,
            "provider": "africastalking",
            "message_id": "ATXid_123",
            "error": None,
            "phone_normalised": "+243812345678",
        }

        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("send_appointment_reminders", stdout=out)

        appt.refresh_from_db()
        self.assertIsNotNone(appt.reminder_sent_at)

        log = AppointmentSMSLog.objects.get(appointment=appt)
        self.assertEqual(log.status, "SUCCESS")
        self.assertEqual(log.message_id, "ATXid_123")
        self.assertEqual(log.phone, "+243812345678")

    @patch("appointments.management.commands.send_appointment_reminders.send_sms")
    @patch("appointments.management.commands.send_appointment_reminders.timezone.now")
    def test_failure_keeps_reminder_null_and_logs(self, mock_now, mock_send):
        """Failed send: reminder_sent_at stays None, FAILED log created."""
        fake_now = datetime(2026, 2, 3, 16, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = fake_now

        scheduled = datetime(2026, 2, 4, 10, 0, tzinfo=CLINIC_TZ)
        appt = self._make_appointment(self.patient, scheduled_at=scheduled)

        mock_send.return_value = {
            "ok": False,
            "provider": "africastalking",
            "message_id": None,
            "error": "Insufficient balance",
            "phone_normalised": "+243812345678",
        }

        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("send_appointment_reminders", stdout=out)

        appt.refresh_from_db()
        self.assertIsNone(appt.reminder_sent_at)

        log = AppointmentSMSLog.objects.get(appointment=appt)
        self.assertEqual(log.status, "FAILED")
        self.assertIn("Insufficient balance", log.error_message)

    @patch("appointments.management.commands.send_appointment_reminders.send_sms")
    @patch("appointments.management.commands.send_appointment_reminders.timezone.now")
    def test_missing_phone_logs_failed(self, mock_now, mock_send):
        """Patient with no phone: FAILED log, send_sms never called."""
        fake_now = datetime(2026, 2, 3, 16, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = fake_now

        scheduled = datetime(2026, 2, 4, 10, 0, tzinfo=CLINIC_TZ)
        appt = self._make_appointment(self.patient_no_phone, scheduled_at=scheduled)

        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("send_appointment_reminders", stdout=out)

        mock_send.assert_not_called()

        log = AppointmentSMSLog.objects.get(appointment=appt)
        self.assertEqual(log.status, "FAILED")
        self.assertIn("missing", log.error_message.lower())

    @patch("appointments.management.commands.send_appointment_reminders.send_sms")
    @patch("appointments.management.commands.send_appointment_reminders.timezone.now")
    def test_before_cutoff_no_send(self, mock_now, mock_send):
        """Running command before 17:00 cutoff: no SMS sent."""
        # 16:00 Kinshasa = 15:00 UTC -> before cutoff
        fake_now = datetime(2026, 2, 3, 15, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = fake_now

        scheduled = datetime(2026, 2, 4, 10, 0, tzinfo=CLINIC_TZ)
        self._make_appointment(self.patient, scheduled_at=scheduled)

        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("send_appointment_reminders", stdout=out)

        mock_send.assert_not_called()
        self.assertEqual(AppointmentSMSLog.objects.count(), 0)

    @patch("appointments.management.commands.send_appointment_reminders.send_sms")
    @patch("appointments.management.commands.send_appointment_reminders.timezone.now")
    def test_scheduled_status_skipped(self, mock_now, mock_send):
        """SCHEDULED status should not even appear in DB query."""
        fake_now = datetime(2026, 2, 3, 16, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = fake_now

        scheduled = datetime(2026, 2, 4, 10, 0, tzinfo=CLINIC_TZ)
        self._make_appointment(self.patient, scheduled_at=scheduled, status="SCHEDULED")

        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("send_appointment_reminders", stdout=out)

        mock_send.assert_not_called()
        output = out.getvalue()
        self.assertIn("No reminders to send", output)


# =========================================================================
# SMS UTF-8 encoding (accented characters)
# =========================================================================
@override_settings(
    AFRICASTALKING_USERNAME="sandbox",
    AFRICASTALKING_API_KEY="test_api_key",
    AFRICASTALKING_SENDER_ID="",
)
class SmsUtf8EncodingTest(TestCase):
    """Verify that French accented characters survive the HTTP encoding round-trip."""

    @patch("appointments.services.sms.http_requests.post")
    def test_accented_message_preserved_in_post_body(self, mock_post):
        """The POST body sent to AT must contain UTF-8 percent-encoded accents."""
        # Simulate a successful AT response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "SMSMessageData": {
                "Recipients": [{"status": "Success", "messageId": "ATXid_utf8"}]
            }
        }
        mock_post.return_value = mock_response

        french_msg = "Médecin pédiatre — février — l'Équipe Clinique"
        result = send_sms("+243812345678", french_msg)

        self.assertTrue(result["ok"])
        mock_post.assert_called_once()

        # Extract the `data` kwarg passed to requests.post
        call_kwargs = mock_post.call_args
        post_data = call_kwargs.kwargs.get("data") or call_kwargs[1].get("data")

        # data should be a dict (requests handles urlencode internally)
        self.assertIsInstance(post_data, dict)
        self.assertEqual(post_data["message"], french_msg)

        # Verify that requests would encode this correctly:
        # simulate what requests.post does with data=dict
        from urllib.parse import urlencode
        encoded = urlencode(post_data, encoding="utf-8")
        # UTF-8 percent-encoding for é is %C3%A9
        self.assertIn("%C3%A9", encoded)  # é in "Médecin"
        # The decoded form must round-trip back to the original message
        decoded = parse_qs(encoded, encoding="utf-8")
        self.assertEqual(decoded["message"][0], french_msg)

    @patch("appointments.services.sms.http_requests.post")
    def test_content_type_includes_utf8_charset(self, mock_post):
        """The Content-Type header must declare charset=UTF-8."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "SMSMessageData": {
                "Recipients": [{"status": "Success", "messageId": "ATXid_hdr"}]
            }
        }
        mock_post.return_value = mock_response

        send_sms("+243812345678", "Test accentué")

        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        content_type = headers.get("Content-Type", "")
        self.assertIn("charset=UTF-8", content_type)

    @patch("appointments.services.sms.http_requests.post")
    def test_full_acceptance_message_round_trips(self, mock_post):
        """The exact acceptance-test message must survive encoding intact."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "SMSMessageData": {
                "Recipients": [{"status": "Success", "messageId": "ATXid_acc"}]
            }
        }
        mock_post.return_value = mock_response

        acceptance_msg = (
            "Bonjour Tracy Masengu, rappel : votre rendez-vous est "
            "demain à 16:30 (4 février 2026) avec le "
            "Dr Mukwamu B. Justin (médecin pédiatre). "
            "Merci d'arriver 10 minutes en avance. "
            "Cordialement, l'Équipe Clinique."
        )
        result = send_sms("+243812345678", acceptance_msg)
        self.assertTrue(result["ok"])

        call_kwargs = mock_post.call_args
        post_data = call_kwargs.kwargs.get("data") or call_kwargs[1].get("data")

        # The raw unicode message must be passed through as-is in the dict
        self.assertEqual(post_data["message"], acceptance_msg)

        # Prove every accented character survives urlencode → parse_qs round-trip
        from urllib.parse import urlencode
        encoded = urlencode(post_data, encoding="utf-8")
        decoded = parse_qs(encoded, encoding="utf-8")
        self.assertEqual(decoded["message"][0], acceptance_msg)

        # Phone number with + must be in the payload (not mangled)
        self.assertEqual(post_data["to"], "+243812345678")

    @patch("appointments.services.sms.http_requests.post")
    def test_non_json_response_handled_gracefully(self, mock_post):
        """A non-JSON response from AT must not crash; error is captured."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = "<html>Gateway Error</html>"
        mock_post.return_value = mock_response

        result = send_sms("+243812345678", "Hello")

        self.assertFalse(result["ok"])
        self.assertIn("Invalid JSON", result["error"])

    @patch("appointments.services.sms.http_requests.post")
    def test_http_error_status_handled(self, mock_post):
        """A 4xx/5xx response must not crash; error includes status code."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = send_sms("+243812345678", "Hello")

        self.assertFalse(result["ok"])
        self.assertIn("HTTP 500", result["error"])

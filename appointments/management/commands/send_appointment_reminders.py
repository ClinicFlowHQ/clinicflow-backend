"""
Management command to send SMS appointment reminders.

Business rules:
- Sends ONE reminder SMS per eligible appointment
- Only on the DAY BEFORE the appointment, starting at 17:00 Africa/Kinshasa
- Only for CONFIRMED or RESCHEDULED appointments with reminders_enabled=True
- Never sends on appointment day (even if <24h away) — missed window
- Records every attempt in AppointmentSMSLog
- Safety cap to prevent mass accidental sends

Designed to run as a Render Cron Job at 16:00 UTC (= 17:00 Africa/Kinshasa).
Can also safely run every 15 minutes; the cutoff logic prevents duplicate/late sends.

Usage: python manage.py send_appointment_reminders
"""

import logging
from datetime import datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import Appointment, AppointmentSMSLog
from appointments.services.sms import mask_phone, send_sms

logger = logging.getLogger(__name__)

# French month names (1-indexed)
_FRENCH_MONTHS = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}

ELIGIBLE_STATUSES = ["CONFIRMED", "RESCHEDULED"]


def format_date_french(dt):
    """Format a datetime as '3 février 2026' (French full month)."""
    return f"{dt.day} {_FRENCH_MONTHS[dt.month]} {dt.year}"


def build_sms_message(patient, scheduled_local):
    """
    Build the personalised French SMS reminder message.

    Uses "Bonjour" before 18:00 Kinshasa, "Bonsoir" after.
    Doctor is fixed: Dr Mukwamu B. Justin - Médecin pédiatre.
    """
    # Salutation based on current Kinshasa time
    tz = ZoneInfo("Africa/Kinshasa")
    now_local = timezone.now().astimezone(tz)
    salutation = "Bonjour" if now_local.hour < 18 else "Bonsoir"

    patient_name = f"{patient.first_name} {patient.last_name}".strip() or "Patient"
    time_str = scheduled_local.strftime("%H:%M")
    date_str = format_date_french(scheduled_local)

    return (
        f"{salutation} {patient_name}, rappel : votre rendez-vous est "
        f"demain à {time_str} ({date_str}) avec le "
        f"Dr Mukwamu B. Justin (médecin pédiatre). "
        f"Merci d'arriver 10 minutes en avance. "
        f"Cordialement, l'Equipe Clinique."
    )


def is_eligible_for_send(appointment, now_local, clinic_tz):
    """
    Apply strict cutoff rule: send only on the day before appointment,
    starting at 17:00 Kinshasa. Never send on appointment day.

    Returns (eligible: bool, reason: str).
    """
    appt_local = appointment.scheduled_at.astimezone(clinic_tz)
    day_before = appt_local.date() - timedelta(days=1)
    cutoff = datetime.combine(day_before, time(17, 0), tzinfo=clinic_tz)

    # Must be at or after the 17:00 cutoff
    if now_local < cutoff:
        return False, "before cutoff (17:00 day before)"

    # Must still be before the appointment time
    if now_local >= appt_local:
        return False, "appointment time has passed"

    # Must be on appointment day minus 1 (not on appointment day itself)
    if now_local.date() >= appt_local.date():
        return False, "already appointment day — missed window"

    # Must be exactly on the day-before date
    if now_local.date() != day_before:
        return False, "not the day before appointment"

    return True, "eligible"


class Command(BaseCommand):
    help = "Send SMS reminders for tomorrow's appointments (17:00 cutoff)"

    def handle(self, *args, **options):
        # -----------------------------------------------------------
        # 1. Timezone setup
        # -----------------------------------------------------------
        tz_name = getattr(settings, "CLINIC_TIMEZONE", "Africa/Kinshasa")
        clinic_tz = ZoneInfo(tz_name)
        now_local = timezone.now().astimezone(clinic_tz)

        self.stdout.write(f"Clinic timezone: {tz_name}")
        self.stdout.write(f"Clinic local time: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")

        # -----------------------------------------------------------
        # 2. Query candidates (broad UTC window, then filter strictly)
        # -----------------------------------------------------------
        # We look for appointments tomorrow OR the day after (to handle
        # edge cases around midnight). The strict cutoff logic filters later.
        tomorrow_date = now_local.date() + timedelta(days=1)
        day_after = tomorrow_date + timedelta(days=1)

        window_start = datetime.combine(tomorrow_date, time.min, tzinfo=clinic_tz)
        window_end = datetime.combine(day_after, time.max, tzinfo=clinic_tz)
        start_utc = window_start.astimezone(dt_timezone.utc)
        end_utc = window_end.astimezone(dt_timezone.utc)

        self.stdout.write(f"Looking for appointments: {tomorrow_date} to {day_after}")
        self.stdout.write(f"Query range (UTC): {start_utc} to {end_utc}")

        candidates = (
            Appointment.objects.filter(
                scheduled_at__gte=start_utc,
                scheduled_at__lt=end_utc,
                status__in=ELIGIBLE_STATUSES,
                reminders_enabled=True,
                reminder_sent_at__isnull=True,
            )
            .select_related("patient")
        )

        total_candidates = candidates.count()
        self.stdout.write(f"Found {total_candidates} candidate(s) from DB query")

        if total_candidates == 0:
            self.stdout.write(self.style.SUCCESS("No reminders to send."))
            return

        # -----------------------------------------------------------
        # 3. Safety cap
        # -----------------------------------------------------------
        max_cap = getattr(settings, "SMS_MAX_REMINDERS_PER_RUN", 200)
        if total_candidates > max_cap:
            msg = (
                f"SAFETY CAP: {total_candidates} candidates exceed limit of {max_cap}. "
                f"Aborting to prevent mass sends. "
                f"Raise SMS_MAX_REMINDERS_PER_RUN if intentional."
            )
            self.stdout.write(self.style.ERROR(msg))
            logger.critical(msg)
            return

        # -----------------------------------------------------------
        # 4. Process each candidate with strict cutoff
        # -----------------------------------------------------------
        sent_count = 0
        failed_count = 0
        skipped_count = 0

        for appointment in candidates:
            patient = appointment.patient

            # --- Strict cutoff check ---
            eligible, reason = is_eligible_for_send(appointment, now_local, clinic_tz)
            if not eligible:
                self.stdout.write(
                    f"  Skip appt #{appointment.id} ({patient}): {reason}"
                )
                skipped_count += 1
                continue

            # --- Check phone ---
            phone_raw = (patient.phone or "").strip()
            if not phone_raw:
                self.stdout.write(
                    self.style.ERROR(f"  No phone for {patient} (appt #{appointment.id})")
                )
                AppointmentSMSLog.objects.create(
                    appointment=appointment,
                    phone="",
                    provider="africastalking",
                    status="FAILED",
                    message_id="",
                    error_message="Patient phone number is missing",
                )
                failed_count += 1
                continue

            # --- Build message ---
            scheduled_local = appointment.scheduled_at.astimezone(clinic_tz)
            message = build_sms_message(patient, scheduled_local)

            masked = mask_phone(phone_raw)
            self.stdout.write(f"  Sending reminder to {patient} at {masked}...")

            # --- Send SMS ---
            result = send_sms(phone_raw, message)

            # --- Log attempt ---
            AppointmentSMSLog.objects.create(
                appointment=appointment,
                phone=result.get("phone_normalised") or phone_raw,
                provider=result.get("provider", "africastalking"),
                status="SUCCESS" if result["ok"] else "FAILED",
                message_id=result.get("message_id") or "",
                error_message=result.get("error") or "",
            )

            if result["ok"]:
                appointment.reminder_sent_at = timezone.now()
                appointment.save(update_fields=["reminder_sent_at"])
                sent_count += 1
                self.stdout.write(self.style.SUCCESS(f"    Sent to {masked}"))
            else:
                failed_count += 1
                err = result.get("error", "unknown")
                self.stdout.write(self.style.ERROR(f"    Failed for {masked}: {err}"))

        # -----------------------------------------------------------
        # 5. Summary
        # -----------------------------------------------------------
        self.stdout.write("")
        self.stdout.write(f"Candidates: {total_candidates}")
        self.stdout.write(f"Skipped (cutoff): {skipped_count}")
        self.stdout.write(self.style.SUCCESS(f"Sent: {sent_count}"))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f"Failed: {failed_count}"))

        logger.info(
            "SMS reminder run: candidates=%d skipped=%d sent=%d failed=%d",
            total_candidates, skipped_count, sent_count, failed_count,
        )
        self.stdout.write(self.style.SUCCESS("Done."))

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0004_appointment_reminder_sent_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="reminders_enabled",
            field=models.BooleanField(default=False),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0003_add_doctor_field"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="reminder_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

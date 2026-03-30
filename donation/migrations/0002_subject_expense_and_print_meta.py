from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def forwards_create_subjects(apps, schema_editor):
    Donation = apps.get_model("donation", "Donation")
    DonationSubject = apps.get_model("donation", "DonationSubject")

    subject_map = {}
    for donation in Donation.objects.all().only("id", "subjected_to"):
        name = (donation.subjected_to or "General").strip() or "General"
        subject = subject_map.get(name)
        if not subject:
            subject, _ = DonationSubject.objects.get_or_create(name=name, defaults={"is_active": True})
            subject_map[name] = subject
        donation.subject_id = subject.id
        donation.save(update_fields=["subject"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("donation", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DonationSubject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="donation_subjects_created", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=150)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("notes", models.TextField(blank=True, null=True)),
                ("expense_date", models.DateField(default=timezone.localdate)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="expenses_created", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-expense_date", "-id"]},
        ),
        migrations.AddField(
            model_name="donation",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="donations_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="donation",
            name="printed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="donation",
            name="printed_by_name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="donation",
            name="subject",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="donations", to="donation.donationsubject"),
        ),
        migrations.RunPython(forwards_create_subjects, reverse_noop),
        migrations.AlterField(
            model_name="donation",
            name="subject",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="donations", to="donation.donationsubject"),
        ),
        migrations.RemoveField(
            model_name="donation",
            name="language",
        ),
        migrations.RemoveField(
            model_name="donation",
            name="subjected_to",
        ),
    ]

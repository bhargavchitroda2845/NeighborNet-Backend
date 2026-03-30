from django.db import migrations, models


def set_one_default_subject(apps, schema_editor):
    DonationSubject = apps.get_model("donation", "DonationSubject")
    default_subject = (
        DonationSubject.objects.filter(name__iexact="General").order_by("id").first()
        or DonationSubject.objects.order_by("id").first()
    )
    if default_subject:
        DonationSubject.objects.exclude(pk=default_subject.pk).update(is_default=False)
        default_subject.is_default = True
        default_subject.save(update_fields=["is_default"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("donation", "0003_expense_subject"),
    ]

    operations = [
        migrations.AddField(
            model_name="donationsubject",
            name="is_default",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_one_default_subject, reverse_noop),
    ]


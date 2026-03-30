from django.db import migrations, models
import django.db.models.deletion


def set_default_subject_for_expenses(apps, schema_editor):
    DonationSubject = apps.get_model("donation", "DonationSubject")
    Expense = apps.get_model("donation", "Expense")

    default_subject, _ = DonationSubject.objects.get_or_create(
        name="General",
        defaults={"is_active": True},
    )
    Expense.objects.filter(subject__isnull=True).update(subject=default_subject)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("donation", "0002_subject_expense_and_print_meta"),
    ]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="subject",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="expenses",
                to="donation.donationsubject",
            ),
        ),
        migrations.RunPython(set_default_subject_for_expenses, reverse_noop),
        migrations.AlterField(
            model_name="expense",
            name="subject",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="expenses",
                to="donation.donationsubject",
            ),
        ),
    ]


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("member", "0010_memberpasswordresettoken"),
    ]

    operations = [
        migrations.CreateModel(
            name="Donation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("address", models.TextField(blank=True, null=True)),
                ("city", models.CharField(blank=True, max_length=120, null=True)),
                ("state", models.CharField(blank=True, max_length=120, null=True)),
                ("country", models.CharField(blank=True, max_length=120, null=True)),
                ("amount_in_words", models.CharField(max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("subjected_to", models.CharField(max_length=255)),
                ("language", models.CharField(choices=[("en", "English"), ("gu", "Gujarati"), ("hi", "Hindi"), ("mr", "Marathi")], default="gu", max_length=2)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="donations", to="member.member")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

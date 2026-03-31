from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("career", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="careerpost",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("inreview", "In Review"),
                    ("published", "Published"),
                    ("rejected", "Rejected"),
                ],
                default="draft",
                max_length=12,
            ),
        ),
    ]

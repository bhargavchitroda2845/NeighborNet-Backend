from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("career", "0003_expand_career_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="careerpost",
            name="image_drive_file_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="image_filename",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

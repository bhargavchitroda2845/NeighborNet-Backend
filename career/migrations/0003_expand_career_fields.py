from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("career", "0002_alter_careerpost_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="careerpost",
            name="contact_person_name",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="contact_person_number",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="current_company_name",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="current_ctc_lpa",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="document_drive_file_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="document_filename",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="enable_compensation",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="enable_document",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="expected_lpa",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="job_title",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="package_lpa",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="responsibilities",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="careerpost",
            name="roles",
            field=models.TextField(blank=True, null=True),
        ),
    ]

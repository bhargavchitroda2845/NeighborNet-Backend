from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("member", "0022_alter_memberdetail_matrimonial_visibility"),
    ]

    operations = [
        migrations.CreateModel(
            name="CareerPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "post_type",
                    models.CharField(
                        choices=[("job_seeker", "Job Seeker"), ("recruiter", "Recruiter")],
                        max_length=20,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("full_name", models.CharField(max_length=150)),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                ("phone", models.CharField(blank=True, max_length=30, null=True)),
                ("location", models.CharField(blank=True, max_length=150, null=True)),
                ("company_name", models.CharField(blank=True, max_length=150, null=True)),
                ("skills", models.CharField(blank=True, max_length=255, null=True)),
                ("experience_years", models.CharField(blank=True, max_length=50, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("inreview", "In Review"),
                            ("published", "Published"),
                            ("rejected", "Rejected"),
                        ],
                        default="published",
                        max_length=12,
                    ),
                ),
                ("created_by_name", models.CharField(blank=True, max_length=150, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("published_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="career_posts",
                        to="member.member",
                    ),
                ),
            ],
            options={
                "verbose_name": "Career Post",
                "verbose_name_plural": "Career Posts",
                "ordering": ["-published_at", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="careerpost",
            index=models.Index(fields=["post_type"], name="career_caree_post_ty_32cff9_idx"),
        ),
        migrations.AddIndex(
            model_name="careerpost",
            index=models.Index(fields=["status"], name="career_caree_status_20b483_idx"),
        ),
        migrations.AddIndex(
            model_name="careerpost",
            index=models.Index(fields=["published_at"], name="career_caree_publish_9ad84e_idx"),
        ),
    ]

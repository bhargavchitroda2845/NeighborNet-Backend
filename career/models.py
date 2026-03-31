from django.db import models
from django.utils import timezone

from member.models import Member


class CareerPost(models.Model):
    POST_TYPE_JOB_SEEKER = "job_seeker"
    POST_TYPE_RECRUITER = "recruiter"
    POST_TYPE_CHOICES = (
        (POST_TYPE_JOB_SEEKER, "Job Seeker"),
        (POST_TYPE_RECRUITER, "Recruiter"),
    )

    STATUS_DRAFT = "draft"
    STATUS_INREVIEW = "inreview"
    STATUS_PUBLISHED = "published"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_INREVIEW, "In Review"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_REJECTED, "Rejected"),
    )

    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField()

    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    location = models.CharField(max_length=150, blank=True, null=True)
    contact_person_name = models.CharField(max_length=150, blank=True, null=True)
    contact_person_number = models.CharField(max_length=30, blank=True, null=True)

    company_name = models.CharField(max_length=150, blank=True, null=True)
    current_company_name = models.CharField(max_length=150, blank=True, null=True)
    roles = models.TextField(blank=True, null=True)
    responsibilities = models.TextField(blank=True, null=True)
    skills = models.CharField(max_length=255, blank=True, null=True)
    experience_years = models.CharField(max_length=50, blank=True, null=True)
    current_ctc_lpa = models.CharField(max_length=50, blank=True, null=True)
    expected_lpa = models.CharField(max_length=50, blank=True, null=True)
    package_lpa = models.CharField(max_length=50, blank=True, null=True)

    enable_compensation = models.BooleanField(default=True)
    enable_document = models.BooleanField(default=True)
    document_drive_file_id = models.CharField(max_length=255, blank=True, null=True)
    document_filename = models.CharField(max_length=255, blank=True, null=True)
    image_drive_file_id = models.CharField(max_length=255, blank=True, null=True)
    image_filename = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        related_name="career_posts",
        blank=True,
        null=True,
    )
    created_by_name = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Career Post"
        verbose_name_plural = "Career Posts"
        indexes = [
            models.Index(fields=["post_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["published_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.status == self.STATUS_PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        elif self.status != self.STATUS_PUBLISHED:
            self.published_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

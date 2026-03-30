from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from member.models import Member  # ✅ Using your custom Member model
# from .models import Categorymodel

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class News(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("inreview", "In Review"),
        ("published", "Published"),
        ("rejected", "Rejected"),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField()

    image = models.ImageField(
        upload_to="news/images/",
        null=True,
        blank=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name="news_items"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="draft"
    )

    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # This field strictly requires a Member instance
    created_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        related_name="news_created"
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_updated"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "News"
        permissions = [
            ("can_review_news", "Can review member news (publish/reject)"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["published_at"]),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate a unique slug from title if not provided
        if not self.slug:
            base_slug = slugify(self.title) or "news"
            slug = base_slug
            counter = 1
            while News.objects.filter(slug=slug).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug

        if self.status == "published" and not self.published_at:
            self.published_at = timezone.now()
        elif self.status != "published":
            self.published_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

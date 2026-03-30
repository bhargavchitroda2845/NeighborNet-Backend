from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from member.models import Member


class BusinessCategory(models.Model):
    """Categories for businesses (Home Work, Tailoring, Shops, Food, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField(max_length=10, blank=True, help_text="Emoji icon for the category")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Business Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Business(models.Model):
    """Business listing model"""
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

    # Basic Info
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    category = models.ForeignKey(
        BusinessCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name="businesses"
    )
    service = models.CharField(max_length=255, help_text="Service type or specialization")
    location = models.CharField(max_length=255, help_text="City or area")
    phone = models.CharField(max_length=50)
    details = models.TextField(blank=True, help_text="Description of services offered")
    
    # Additional Info
    image = models.ImageField(upload_to="business/images/", blank=True, null=True)
    address = models.TextField(blank=True)
    area = models.CharField(max_length=255, blank=True)
    working_hours = models.CharField(max_length=255, blank=True, help_text="e.g., 9 AM - 6 PM")
    
    # Pricing
    price_range_min = models.IntegerField(blank=True, null=True)
    price_range_max = models.IntegerField(blank=True, null=True)
    
    # Status
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Timestamps and User
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        related_name="business_created",
        blank=True,
        null=True,
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        related_name="business_updated",
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "business"
        ordering = ["-published_at"]
        verbose_name = "Business"
        verbose_name_plural = "Businesses"
        permissions = [
            ("can_review_business", "Can review member business (publish/reject)"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["published_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base_slug = slugify(self.name) or "business"
            candidate = base_slug
            counter = 1
            while Business.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = candidate

        if self.status == self.STATUS_PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        elif self.status != self.STATUS_PUBLISHED:
            self.published_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def price_range(self):
        if self.price_range_min and self.price_range_max:
            return f"₹{self.price_range_min} - ₹{self.price_range_max}"
        elif self.price_range_min:
            return f"₹{self.price_range_min}+"
        return None


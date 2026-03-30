from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from member.models import Member


class BnsModel(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_INREVIEW = "inreview"
    STATUS_PUBLISHED = "published"
    STATUS_REJECTED = "rejected"
    STATUS_SOLD = "sold"
    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_INREVIEW, "In Review"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_SOLD, "Sold"),
    )

    LISTING_TYPE_BUYER = "buyer"
    LISTING_TYPE_SELLER = "seller"
    LISTING_TYPE_RENTAL = "rental"

    LISTING_TYPE_CHOICES = (
        (LISTING_TYPE_BUYER, "Buyer"),
        (LISTING_TYPE_SELLER, "Seller"),
        (LISTING_TYPE_RENTAL, "Rental"),
    )

    id = models.AutoField(primary_key=True, unique=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    desc = models.TextField()
    image = models.ImageField(upload_to="marketplace/images/", blank=True, null=True)
    listing_type = models.CharField(max_length=20, choices=LISTING_TYPE_CHOICES)
    area = models.CharField(max_length=255, blank=True, null=True)
    contact = models.CharField(max_length=50)
    min_price = models.IntegerField(blank=True, null=True)
    max_price = models.IntegerField(blank=True, null=True)
    price = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        related_name="bns_created",
        blank=True,
        null=True,
    )
    created_by_username = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        related_name="bns_updated",
        blank=True,
        null=True,
    )
    updated_by_username = models.CharField(max_length=150, blank=True, null=True)
    bidding_enabled = models.BooleanField(default=False, help_text="Enable bidding for this item")

    class Meta:
        db_table = "bns_model"
        ordering = ["-published_at"]
        verbose_name = "BNS"
        verbose_name_plural = "BNS"

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            base_slug = slugify(self.title) or "bns-item"
            candidate = base_slug
            counter = 1
            while BnsModel.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = candidate

        if self.status == self.STATUS_PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        elif self.status != self.STATUS_PUBLISHED:
            self.published_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Bid(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
    )

    marketplace_item = models.ForeignKey(
        BnsModel,
        on_delete=models.CASCADE,
        related_name="bids"
    )
    bidder = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="bids_placed"
    )
    bid_amount = models.IntegerField()
    message = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    is_winner = models.BooleanField(default=False, help_text="Mark this bid as the winning bid")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bid"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Bid {self.bid_amount} by {self.bidder} on {self.marketplace_item}"

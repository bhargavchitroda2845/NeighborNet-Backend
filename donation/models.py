from django.conf import settings
from django.db import models
from django.utils import timezone

from member.models import Member


class DonationSubject(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donation_subjects_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "name"]

    def __str__(self):
        return self.name


class Donation(models.Model):
    subject = models.ForeignKey(
        DonationSubject,
        on_delete=models.PROTECT,
        related_name="donations",
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="donations",
    )
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=120, blank=True, null=True)
    state = models.CharField(max_length=120, blank=True, null=True)
    country = models.CharField(max_length=120, blank=True, null=True)
    amount_in_words = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations_created",
    )
    printed_at = models.DateTimeField(blank=True, null=True)
    printed_by_name = models.CharField(max_length=120, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Donation #{self.id} - Member {self.member_id}"


class Expense(models.Model):
    subject = models.ForeignKey(
        DonationSubject,
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    expense_date = models.DateField(default=timezone.localdate)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expense_date", "-id"]

    def __str__(self):
        return f"Expense #{self.id} - {self.title}"

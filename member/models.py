from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from datetime import timedelta
import secrets
import string
import re


User = get_user_model()


class Country(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name


class State(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="states")
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]
        unique_together = ("country", "name")

    def __str__(self):
        return f"{self.name} ({self.country.name})"


class City(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="cities")
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="cities",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=120)

    class Meta:
        unique_together = ("country", "state", "id")

    def __str__(self):
        if self.state:
            return f"{self.name} ({self.state.name}, {self.country.name})"
        return f"{self.name} ({self.country.name})"


class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    member_no = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    surname = models.CharField(max_length=50)
    phone_no = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.PositiveIntegerField(blank=True, null=True)

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    occupation = models.CharField(max_length=100, blank=True, null=True)
    email_id = models.EmailField(max_length=254, blank=True, null=True)
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="members",
        blank=True,
        null=True,
    )
    state = models.ForeignKey(
        State,
        on_delete=models.PROTECT,
        related_name="members",
        blank=True,
        null=True,
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="members",
        blank=True,
        null=True,
    )
    residential_address = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to="member/profile/", blank=True, null=True)

    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
    ]
    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
        blank=True,
        null=True,
    )
    education = models.CharField(max_length=120, blank=True, null=True)

    username = models.CharField(max_length=50, unique=True, blank=True, null=True)
    password = models.CharField(max_length=128, blank=True, null=True)

    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Inactive", "Inactive"),
        ("Blocked", "Blocked"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Inactive")

    APPROVAL_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Not Approved", "Not Approved"),
    ]
    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_CHOICES, default="Pending"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approved_members",
        help_text="The admin user who approved this member",
    )
    approved_at = models.DateTimeField(blank=True, null=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="member_created",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="member_updated",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def generate_unique_username(cls, first_name, surname, phone_no=None):
        base_first = (first_name or "").strip().lower()
        base_surname = (surname or "").strip().lower()
        base = f"{base_first}{base_surname}"
        base = re.sub(r"[^a-z0-9]", "", base)
        if not base:
            base = "member"

        username = base
        counter = 1
        while cls.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        return username

    @staticmethod
    def generate_temp_password(length=10):
        alphabet = string.ascii_letters + string.digits + "@#$%"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def approve(self, approver=None):
        if not self.username:
            self.username = self.generate_unique_username(self.first_name, self.surname, self.phone_no)

        raw_password = self.generate_temp_password()
        self.password = raw_password
        self.status = "Active"
        self.approval_status = "Approved"
        self.approved_by = approver
        self.approved_at = timezone.now()
        self.save()
        return raw_password

    def mark_not_approved(self, approver=None):
        self.status = "Inactive"
        self.approval_status = "Not Approved"
        self.approved_by = approver
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "approval_status", "approved_by", "approved_at", "updated_at"])

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save(update_fields=["password", "updated_at"])
        if self.user_id:
            self.user.set_password(raw_password)
            self.user.save(update_fields=["password"])

    def check_password(self, raw_password):
        return check_password(raw_password, self.password or "")

    def __str__(self):
        return f"{self.member_no} - {self.first_name} {self.surname}"


class MemberDetail(models.Model):
    member_id = models.AutoField(primary_key=True)
    member_no = models.ForeignKey(
        "member.Member",
        on_delete=models.CASCADE,
        related_name="details",
    )

    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    surname = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.PositiveIntegerField()

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    occupation = models.CharField(max_length=100, blank=True, null=True)
    email_id = models.EmailField(max_length=254, blank=True, null=True)
    profile_image = models.ImageField(upload_to="member/profile/", blank=True, null=True)

    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
    ]
    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
        blank=True,
        null=True,
    )
    education = models.CharField(max_length=120, blank=True, null=True)

    # ── Matrimonial Fields ──────────────────────────────────────────────────────
    show_on_matrimonial = models.BooleanField(default=False)
    is_matrimonial_public = models.BooleanField(default=False)

    VISIBILITY_CHOICES = [
        ("Public", "Public"),
        ("Protected", "Protected"),
    ]
    matrimonial_visibility = models.CharField(
        max_length=20, 
        choices=VISIBILITY_CHOICES, 
        default="Public", 
        help_text="Public: show to all without login. Protected: show to logged in users."
    )

    RELATION_CHOICES = [
        ("self", "Self"),
        ("son", "Son"),
        ("daughter", "Daughter"),
        ("brother", "Brother"),
        ("sister", "Sister"),
        ("relative", "Relative"),
    ]
    relation_with_member = models.CharField(
        max_length=20, choices=RELATION_CHOICES, blank=True, null=True
    )

    BLOOD_GROUP_CHOICES = [
        ("A+", "A+"), ("A-", "A-"),
        ("B+", "B+"), ("B-", "B-"),
        ("AB+", "AB+"), ("AB-", "AB-"),
        ("O+", "O+"), ("O-", "O-"),
    ]
    blood_group = models.CharField(
        max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True, null=True
    )

    MANGLIK_CHOICES = [
        ("yes", "Yes"),
        ("no", "No"),
        ("dont_know", "Don't Know"),
    ]
    height = models.CharField(max_length=20, blank=True, null=True, help_text="e.g. 5'7\"")
    gotra = models.CharField(max_length=100, blank=True, null=True)
    manglik = models.CharField(max_length=20, choices=MANGLIK_CHOICES, blank=True, null=True)
    annual_income = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 5-7 LPA")
    about_matrimonial = models.TextField(blank=True, null=True)
    matrimonial_photo = models.ImageField(
        upload_to="member/matrimonial/", blank=True, null=True
    )

    # ── Extended Matrimonial Fields ─────────────────────────────────────────────
    addictions = models.CharField(
        max_length=200, blank=True, null=True, 
        help_text="e.g. Smoke, Drink (comma separated)"
    )

    DIET_CHOICES = [
        ("vegetarian", "Vegetarian"),
        ("swaminarayan", "Swaminarayan"),
        ("non_vegetarian", "Non-Vegetarian"),
        ("eggetarian", "Eggetarian"),
        ("vegan", "Vegan"),
        ("jain", "Jain"),
    ]
    diet = models.CharField(max_length=20, choices=DIET_CHOICES, blank=True, null=True)

    # Family Details
    father_name = models.CharField(max_length=100, blank=True, null=True)
    mother_name = models.CharField(max_length=100, blank=True, null=True)

    FAMILY_TYPE_CHOICES = [
        ("nuclear", "Nuclear"),
        ("joint", "Joint"),
        ("extended", "Extended"),
    ]
    family_type = models.CharField(max_length=20, choices=FAMILY_TYPE_CHOICES, blank=True, null=True)
    siblings = models.CharField(max_length=200, blank=True, null=True, help_text="e.g. 1 younger sister (married)")

    # Additional Bio & Contact
    contact_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Public contact number for matrimonial")
    full_bio = models.TextField(blank=True, null=True, help_text="Detailed biodata")
    hobbies = models.CharField(max_length=255, blank=True, null=True)
    partner_preference = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        related_name="memberdetail_created",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        related_name="memberdetail_updated",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Detail of {self.member_no}"


class MemberPasswordResetToken(models.Model):
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def is_valid(self):
        return (not self.is_used) and (not self.is_expired)

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

    @classmethod
    def create_for_member(cls, member, ttl_minutes=30):
        cls.objects.filter(member=member, used_at__isnull=True).update(used_at=timezone.now())
        token = secrets.token_urlsafe(48)
        expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
        return cls.objects.create(member=member, token=token, expires_at=expires_at)


class OTPVerification(models.Model):
    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def is_expired(self):
        # OTP is valid for 10 minutes
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"{self.email} - {self.otp_code} (Verified: {self.is_verified})"

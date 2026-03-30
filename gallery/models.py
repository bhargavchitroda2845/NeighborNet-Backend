from django.db import models
from django.utils.text import slugify
from django.utils import timezone
import json
from member.models import Member


class GalleryAlbum(models.Model):
    """Gallery Album model with approval workflow similar to news/marketplace"""
    
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
    
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_PROTECTED = "protected"
    VISIBILITY_PRIVATE = "private"
    
    VISIBILITY_CHOICES = (
        (VISIBILITY_PUBLIC, "Public"),
        (VISIBILITY_PROTECTED, "Protected (Logged In Users)"),
        (VISIBILITY_PRIVATE, "Private (Owner Only)"),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    cover_image = models.ImageField(
        upload_to="gallery/albums/",
        blank=True,
        null=True
    )
    
    member = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        related_name="gallery_albums"
    )
    
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC
    )
    
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    google_drive_file_id = models.CharField(max_length=255, blank=True, null=True)
    drive_folder_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Gallery Album"
        verbose_name_plural = "Gallery Albums"
        permissions = [
            ("can_review_gallery", "Can review member gallery albums"),
        ]

    @property
    def display_url(self):
        from django.urls import reverse
        if self.google_drive_file_id:
            try:
                return reverse('gallery:drive_image_serve', kwargs={'file_id': self.google_drive_file_id})
            except:
                pass
        return self.cover_image.url if self.cover_image else None
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["visibility"]),
            models.Index(fields=["published_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            base_slug = slugify(self.title) or "album"
            candidate = base_slug
            counter = 1
            while GalleryAlbum.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
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
    
    @property
    def image_count(self):
        """Return count of published images only"""
        return self.images.filter(status="published").count()
    
    @property
    def all_image_count(self):
        """Return count of all images"""
        return self.images.count()


class GalleryImage(models.Model):
    """Gallery Image model belonging to an album with individual approval workflow"""
    
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
    
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_PROTECTED = "protected"
    VISIBILITY_PRIVATE = "private"
    
    VISIBILITY_CHOICES = (
        (VISIBILITY_PUBLIC, "Public"),
        (VISIBILITY_PROTECTED, "Protected (Logged In Users)"),
        (VISIBILITY_PRIVATE, "Private (Owner Only)"),
    )
    
    album = models.ForeignKey(
        GalleryAlbum,
        on_delete=models.CASCADE,
        related_name="images"
    )
    
    image = models.ImageField(
        upload_to="gallery/images/",
        blank=False,
        null=False
    )
    
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    order = models.PositiveIntegerField(default=0)
    
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC
    )
    
    # Individual image status for review workflow
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_INREVIEW  # Images go to inreview when added
    )
    
    google_drive_file_id = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    @property
    def display_url(self):
        from django.urls import reverse
        if self.google_drive_file_id:
            try:
                return reverse('gallery:drive_image_serve', kwargs={'file_id': self.google_drive_file_id})
            except:
                pass
        return self.image.url if self.image else None

    class Meta:
        ordering = ["order", "created_at"]
        verbose_name = "Gallery Image"
        verbose_name_plural = "Gallery Images"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["visibility"]),
        ]

    def save(self, *args, **kwargs):
        if self.status == self.STATUS_PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        elif self.status != self.STATUS_PUBLISHED:
            self.published_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        if self.title:
            return self.title
        return f"Image {self.id} in {self.album.title}"



class GoogleDriveConnection(models.Model):
    """Stores Google Drive OAuth credentials and bb_album folder ID for a member"""
    member = models.OneToOneField(
        Member, 
        on_delete=models.CASCADE, 
        related_name="google_drive_connection"
    )
    folder_id = models.CharField(max_length=255, blank=True, null=True, help_text="The ID of the 'bb_album' folder")
    credentials_data = models.TextField(blank=True, null=True, help_text="Serialized OAuth2 credentials")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Google Drive Connection"
        verbose_name_plural = "Google Drive Connections"

    def __str__(self):
        return f"Drive Connection for {self.member.username}"

    def set_credentials(self, credentials):
        """Helper to serialize credentials object to JSON"""
        self.credentials_data = json.dumps({
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        })

    def get_credentials_dict(self):
        """Helper to deserialize credentials JSON to dict"""
        if self.credentials_data:
            return json.loads(self.credentials_data)
        return None


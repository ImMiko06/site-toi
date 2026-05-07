from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.hashers import check_password, is_password_usable, make_password
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


def event_asset_path(instance, filename):
    ext = Path(filename).suffix.lower()
    return f"weddings/{instance.slug}/event/{uuid4().hex}{ext}"


def guest_avatar_path(instance, filename):
    ext = Path(filename).suffix.lower()
    return f"weddings/{instance.event.slug}/avatars/{instance.id or uuid4().hex}{ext}"


def media_upload_path(instance, filename):
    ext = Path(filename).suffix.lower()
    return f"weddings/{instance.event.slug}/posts/{instance.author_id}/{uuid4().hex}{ext}"


class WeddingEvent(models.Model):
    """A single wedding/toy microsite with schedule, archive, and invite data."""

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=160)
    groom_name = models.CharField(max_length=80)
    bride_name = models.CharField(max_length=80)
    venue_name = models.CharField(max_length=160, blank=True)
    venue_address = models.CharField(max_length=255, blank=True)
    starts_at = models.DateTimeField()
    upload_start = models.DateTimeField()
    upload_end = models.DateTimeField()
    invitation_title = models.CharField(max_length=160, blank=True)
    invitation_text = models.TextField(blank=True)
    couple_photo = models.FileField(upload_to=event_asset_path, blank=True)
    archive_cover = models.FileField(upload_to=event_asset_path, blank=True)
    videographer_film_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.upload_end <= self.upload_start:
            raise ValidationError({"upload_end": "Upload end must be after upload start."})

    @property
    def has_started(self):
        return timezone.now() >= self.starts_at

    @property
    def is_archive_mode(self):
        return timezone.now() > self.upload_end

    def is_upload_window_open(self, at=None):
        current = at or timezone.now()
        return self.upload_start <= current <= self.upload_end


class ReceptionTable(models.Model):
    event = models.ForeignKey(WeddingEvent, on_delete=models.CASCADE, related_name="tables")
    name = models.CharField(max_length=80)
    number = models.PositiveSmallIntegerField()
    capacity = models.PositiveSmallIntegerField(default=10)
    is_vip = models.BooleanField(default=False)
    position_x = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    position_y = models.DecimalField(max_digits=5, decimal_places=2, default=50)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["event", "number"], name="unique_table_number_per_event"),
            models.UniqueConstraint(fields=["event", "name"], name="unique_table_name_per_event"),
        ]

    def __str__(self):
        return f"{self.event.title}: {self.name}"


class WeddingGuest(models.Model):
    class UploadOverride(models.TextChoices):
        AUTO = "auto", "Automatic schedule"
        ALLOW = "allow", "Manual author"
        DENY = "deny", "Manual blocked"

    event = models.ForeignKey(WeddingEvent, on_delete=models.CASCADE, related_name="guests")
    table = models.ForeignKey(
        ReceptionTable,
        on_delete=models.SET_NULL,
        related_name="guests",
        blank=True,
        null=True,
    )
    nickname = models.CharField(max_length=40, validators=[MinLengthValidator(2)])
    display_name = models.CharField(max_length=120, blank=True)
    password_hash = models.CharField(max_length=128)
    avatar = models.FileField(upload_to=guest_avatar_path, blank=True)
    upload_override = models.CharField(
        max_length=8,
        choices=UploadOverride.choices,
        default=UploadOverride.AUTO,
        help_text="AUTO uses event upload_start/upload_end; ALLOW grants; DENY blocks.",
    )
    is_active = models.BooleanField(default=True)
    is_host = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["nickname"]
        constraints = [
            models.UniqueConstraint(fields=["event", "nickname"], name="unique_guest_nickname_per_event")
        ]

    def __str__(self):
        return self.display_name or self.nickname

    @property
    def initials(self):
        return (self.display_name or self.nickname)[:1].upper()

    @property
    def is_author(self):
        return self.upload_override == self.UploadOverride.ALLOW

    @property
    def has_login_access(self):
        return is_password_usable(self.password_hash)

    def set_password(self, raw_password):
        if len(raw_password or "") < 6:
            raise ValidationError("Password must contain at least 6 characters.")
        self.password_hash = make_password(raw_password)

    def set_unusable_password(self):
        self.password_hash = make_password(None)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def can_upload(self, at=None):
        if not self.is_active:
            return False
        if self.upload_override == self.UploadOverride.ALLOW:
            return True
        if self.upload_override == self.UploadOverride.DENY:
            return False
        return self.event.is_upload_window_open(at=at)


class TableSeat(models.Model):
    event = models.ForeignKey(WeddingEvent, on_delete=models.CASCADE, related_name="seats")
    table = models.ForeignKey(ReceptionTable, on_delete=models.CASCADE, related_name="seats")
    guest = models.OneToOneField(WeddingGuest, on_delete=models.CASCADE, related_name="seat")
    seat_number = models.PositiveSmallIntegerField(blank=True, null=True)
    note = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["table__number", "seat_number", "guest__nickname"]
        constraints = [
            models.UniqueConstraint(fields=["event", "guest"], name="unique_guest_seat_per_event"),
            models.UniqueConstraint(
                fields=["table", "seat_number"],
                condition=Q(seat_number__isnull=False),
                name="unique_numbered_seat_per_table",
            ),
        ]

    def clean(self):
        if self.table.event_id != self.event_id or self.guest.event_id != self.event_id:
            raise ValidationError("Seat, table, and guest must belong to the same wedding event.")

    def __str__(self):
        return f"{self.guest} at {self.table}"


class UploadAccessRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        APPROVED = "approved", "Одобрено"
        REJECTED = "rejected", "Отклонено"

    event = models.ForeignKey(WeddingEvent, on_delete=models.CASCADE, related_name="upload_requests")
    guest = models.ForeignKey(WeddingGuest, on_delete=models.CASCADE, related_name="upload_requests")
    message = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    admin_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_upload_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заявка на загрузку"
        verbose_name_plural = "Заявки на загрузку"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event", "status", "-created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "guest"],
                condition=Q(status="pending"),
                name="unique_pending_upload_request_per_guest",
            )
        ]

    def __str__(self):
        return f"{self.guest} · {self.get_status_display()}"

    def approve(self, user=None):
        self.status = self.Status.APPROVED
        self.reviewed_at = timezone.now()
        self.reviewed_by = user
        self.guest.upload_override = WeddingGuest.UploadOverride.ALLOW
        self.guest.save(update_fields=["upload_override"])
        self.save(update_fields=["status", "reviewed_at", "reviewed_by", "updated_at"])

    def reject(self, user=None):
        self.status = self.Status.REJECTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = user
        self.save(update_fields=["status", "reviewed_at", "reviewed_by", "updated_at"])


class MediaPost(models.Model):
    class MediaType(models.TextChoices):
        PHOTO = "photo", "Фото"
        VIDEO = "video", "Видео"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending moderation"
        APPROVED = "approved", "Approved"
        HIDDEN = "hidden", "Hidden"

    event = models.ForeignKey(WeddingEvent, on_delete=models.CASCADE, related_name="media_posts")
    author = models.ForeignKey(WeddingGuest, on_delete=models.CASCADE, related_name="media_posts")
    media_type = models.CharField(max_length=8, choices=MediaType.choices)
    file = models.FileField(upload_to=media_upload_path, blank=True)
    external_url = models.CharField(max_length=255, blank=True)
    thumbnail = models.FileField(upload_to=media_upload_path, blank=True)
    caption = models.CharField(max_length=240, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.APPROVED)
    width = models.PositiveIntegerField(blank=True, null=True)
    height = models.PositiveIntegerField(blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)
    file_size_bytes = models.PositiveBigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "-created_at"]),
            models.Index(fields=["event", "status", "-created_at"]),
            models.Index(fields=["author", "-created_at"]),
        ]

    def clean(self):
        if self.author_id and self.event_id and self.author.event_id != self.event_id:
            raise ValidationError("Author must belong to the same wedding event.")
        if self._state.adding and self.author_id and not self.author.can_upload():
            raise ValidationError("This guest is not allowed to upload media right now.")
        if not self.file and not self.external_url:
            raise ValidationError("Media post requires an uploaded file or external URL.")

    @property
    def media_url(self):
        if self.file:
            return self.file.url
        return self.external_url

    def __str__(self):
        return f"{self.author} - {self.media_type} - {self.created_at:%Y-%m-%d}"


class MediaLike(models.Model):
    post = models.ForeignKey(MediaPost, on_delete=models.CASCADE, related_name="likes")
    guest = models.ForeignKey(WeddingGuest, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["post", "guest"], name="unique_like_per_guest_post")
        ]

    def clean(self):
        if self.post_id and self.guest_id and self.post.event_id != self.guest.event_id:
            raise ValidationError("Guest and post must belong to the same wedding event.")

    def __str__(self):
        return f"{self.guest} liked #{self.post_id}"


class MediaComment(models.Model):
    class Status(models.TextChoices):
        VISIBLE = "visible", "Visible"
        HIDDEN = "hidden", "Hidden"

    post = models.ForeignKey(MediaPost, on_delete=models.CASCADE, related_name="comments")
    guest = models.ForeignKey(WeddingGuest, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField(max_length=500)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.VISIBLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["post", "status", "created_at"])]

    def clean(self):
        if self.post_id and self.guest_id and self.post.event_id != self.guest.event_id:
            raise ValidationError("Guest and post must belong to the same wedding event.")
        if self._state.adding and self.post_id and not self.post.event.is_upload_window_open():
            raise ValidationError("Comments are closed outside the live upload window.")

    def __str__(self):
        return f"{self.guest}: {self.body[:40]}"

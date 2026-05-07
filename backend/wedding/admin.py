from django.contrib import admin

from .models import (
    MediaComment,
    MediaLike,
    MediaPost,
    ReceptionTable,
    TableSeat,
    UploadAccessRequest,
    WeddingEvent,
    WeddingGuest,
)


@admin.register(WeddingEvent)
class WeddingEventAdmin(admin.ModelAdmin):
    list_display = ("title", "starts_at", "upload_start", "upload_end", "is_published")
    list_filter = ("is_published",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(WeddingGuest)
class WeddingGuestAdmin(admin.ModelAdmin):
    list_display = ("nickname", "display_name", "event", "table", "upload_override", "is_active")
    list_filter = ("event", "upload_override", "is_active", "is_host")
    search_fields = ("nickname", "display_name")


@admin.register(ReceptionTable)
class ReceptionTableAdmin(admin.ModelAdmin):
    list_display = ("event", "number", "name", "capacity", "is_vip")
    list_filter = ("event", "is_vip")


@admin.register(TableSeat)
class TableSeatAdmin(admin.ModelAdmin):
    list_display = ("event", "table", "guest", "seat_number")
    list_filter = ("event", "table")


@admin.register(MediaPost)
class MediaPostAdmin(admin.ModelAdmin):
    list_display = ("event", "author", "media_type", "status", "created_at")
    list_filter = ("event", "media_type", "status")
    search_fields = ("author__nickname", "caption")


@admin.action(description="Одобрить выбранные заявки на загрузку")
def approve_upload_requests(modeladmin, request, queryset):
    for upload_request in queryset.select_related("guest"):
        upload_request.approve(user=request.user)


@admin.action(description="Отклонить выбранные заявки на загрузку")
def reject_upload_requests(modeladmin, request, queryset):
    for upload_request in queryset:
        upload_request.reject(user=request.user)


@admin.register(UploadAccessRequest)
class UploadAccessRequestAdmin(admin.ModelAdmin):
    list_display = ("guest", "event", "status", "created_at", "reviewed_at", "reviewed_by")
    list_filter = ("event", "status", "created_at")
    search_fields = ("guest__nickname", "guest__display_name", "message")
    readonly_fields = ("created_at", "updated_at", "reviewed_at", "reviewed_by")
    actions = [approve_upload_requests, reject_upload_requests]

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = UploadAccessRequest.objects.filter(pk=obj.pk).values_list("status", flat=True).first()

        super().save_model(request, obj, form, change)

        if obj.status == UploadAccessRequest.Status.APPROVED and old_status != UploadAccessRequest.Status.APPROVED:
            obj.approve(user=request.user)
        elif obj.status == UploadAccessRequest.Status.REJECTED and old_status != UploadAccessRequest.Status.REJECTED:
            obj.reject(user=request.user)


admin.site.register(MediaLike)
admin.site.register(MediaComment)

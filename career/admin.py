from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html

from .models import CareerPost


@admin.register(CareerPost)
class CareerPostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "post_type_badge",
        "title",
        "full_name",
        "company_name",
        "compensation_value",
        "document_status",
        "location",
        "status_badge",
        "created_at",
    )
    list_filter = ("post_type", "status", "created_at")
    search_fields = ("title", "description", "full_name", "company_name", "skills", "location")
    readonly_fields = ("created_at", "updated_at", "published_at")
    actions = ("publish_selected", "reject_selected")

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        if "current_ctc_lpa" in form.base_fields:
            form.base_fields["current_ctc_lpa"].label = "Current CTC: ___(LPA)"
        if "expected_lpa" in form.base_fields:
            form.base_fields["expected_lpa"].label = "Expected CTC: ___(LPA)"
        if "package_lpa" in form.base_fields:
            form.base_fields["package_lpa"].label = "Package: ___(LPA)"
        return form

    def post_type_badge(self, obj):
        color = "#0ea5e9" if obj.post_type == CareerPost.POST_TYPE_RECRUITER else "#22c55e"
        label = obj.get_post_type_display()
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:999px;font-size:11px;">{}</span>',
            color,
            label,
        )

    post_type_badge.short_description = "Type"

    def status_badge(self, obj):
        color_map = {
            CareerPost.STATUS_PUBLISHED: "#28a745",
            CareerPost.STATUS_DRAFT: "#ffc107",
            CareerPost.STATUS_INREVIEW: "#007bff",
            CareerPost.STATUS_REJECTED: "#dc3545",
        }
        color = color_map.get(obj.status, "#6c757d")
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:999px;font-size:11px;">{}</span>',
            color,
            label,
        )

    status_badge.short_description = "Status"

    def compensation_value(self, obj):
        if obj.post_type == CareerPost.POST_TYPE_RECRUITER:
            return f"{obj.package_lpa} (LPA)" if obj.package_lpa else "-"
        value = obj.expected_lpa or obj.current_ctc_lpa
        return f"{value} (LPA)" if value else "-"

    compensation_value.short_description = "CTC: ___(LPA)"

    def document_status(self, obj):
        if obj.document_filename:
            return obj.document_filename
        return "-"

    document_status.short_description = "PDF"

    @admin.action(description="Publish selected career posts")
    def publish_selected(self, request, queryset):
        updated = queryset.exclude(status=CareerPost.STATUS_PUBLISHED).update(status=CareerPost.STATUS_PUBLISHED)
        self.message_user(request, f"Published {updated} career post(s).", level=messages.SUCCESS)

    @admin.action(description="Reject selected career posts")
    def reject_selected(self, request, queryset):
        updated = queryset.exclude(status=CareerPost.STATUS_REJECTED).update(status=CareerPost.STATUS_REJECTED)
        self.message_user(request, f"Rejected {updated} career post(s).", level=messages.WARNING)

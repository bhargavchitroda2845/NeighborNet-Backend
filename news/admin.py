from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.db.models import Case, DateTimeField, F, IntegerField, Value, When
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from django.urls import reverse
from .models import News, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(News)
class NewsAdmin(admin.ModelAdmin): # Rename class to NewsAdmin to avoid conflict with model name
    list_display = (
        "image_preview",
        "title",
        "category_badge",
        "status_badge",
        "created_by",
        "created_at",
        "action_buttons",
    )

    list_filter = (
        "status",
        "category",
    )

    search_fields = ("title", "content")
    list_per_page = 10
    list_max_show_all = 200
    sortable_by = ()

    prepopulated_fields = {
        "slug": ("title",)
    }

    readonly_fields = ("image_preview", "created_at", "updated_at", "created_by", "updated_by")
    actions = ("publish_selected", "reject_selected")

    def _can_review_news(self, request):
        return request.user.is_superuser or request.user.has_perm("news.can_review_news")

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:48px; width:48px; object-fit:cover; border-radius:4px;" />',
                obj.image.url,
            )
        return "-"
    image_preview.short_description = "Image"

    def category_badge(self, obj):
        if not obj.category:
            return format_html('<span style="color:#6c757d;">Uncategorized</span>')
        return format_html(
            '<span style="background:#17a2b8;color:#fff;padding:2px 8px;border-radius:999px;font-size:11px;">{}</span>',
            obj.category.name,
        )
    category_badge.short_description = "Category"

    def status_badge(self, obj):
        color_map = {
            "published": "#28a745",
            "draft": "#ffc107",
            "inreview": "#007bff",
            "rejected": "#dc3545",
        }
        color = color_map.get(obj.status, "#6c757d")
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:999px;font-size:11px;">{}</span>',
            color,
            label,
        )
    status_badge.short_description = "Status"

    def action_buttons(self, obj):
        edit_url = reverse("admin:news_news_change", args=[obj.id])
        delete_url = reverse("admin:news_news_delete", args=[obj.id])

        return format_html(
            '''
            <a class="button" style="padding:2px 5px; background:#447e9b; color:white; border-radius:4px;" href="{}">Edit</a>
            <a class="button" style="padding:2px 5px; background:#ba2121; color:white; border-radius:4px;" href="{}">Delete</a>
            ''',
            edit_url,
            delete_url
        )

    action_buttons.short_description = "Actions"

    @admin.action(description="Publish selected news")
    def publish_selected(self, request, queryset):
        if not self._can_review_news(request):
            raise PermissionDenied("You do not have permission to publish news.")

        updated = 0
        reviewer_member = getattr(request.user, "member", None)
        for obj in queryset:
            if obj.status == "published":
                continue
            obj.status = "published"
            if reviewer_member:
                obj.updated_by = reviewer_member
            obj.save()
            updated += 1

        self.message_user(request, f"Published {updated} news item(s).", level=messages.SUCCESS)

    @admin.action(description="Reject selected news")
    def reject_selected(self, request, queryset):
        if not self._can_review_news(request):
            raise PermissionDenied("You do not have permission to reject news.")

        updated = 0
        reviewer_member = getattr(request.user, "member", None)
        for obj in queryset:
            if obj.status == "rejected":
                continue
            obj.status = "rejected"
            if reviewer_member:
                obj.updated_by = reviewer_member
            obj.save()
            updated += 1

        self.message_user(request, f"Rejected {updated} news item(s).", level=messages.WARNING)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not self._can_review_news(request):
            actions.pop("publish_selected", None)
            actions.pop("reject_selected", None)
        return actions

    def changelist_view(self, request, extra_context=None):
        if "o" in request.GET:
            query = request.GET.copy()
            query.pop("o", None)
            qs = query.urlencode()
            redirect_url = request.path if not qs else f"{request.path}?{qs}"
            return HttpResponseRedirect(redirect_url)
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            status_order=Case(
                When(status="inreview", then=Value(0)),
                When(status="rejected", then=Value(1)),
                When(status="published", then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            ),
            sort_time=Case(
                When(status="inreview", then=F("updated_at")),
                When(status="published", then=Coalesce("published_at", "updated_at", "created_at")),
                default=F("updated_at"),
                output_field=DateTimeField(),
            ),
        ).order_by("status_order", "-sort_time", "-id")

    def save_model(self, request, obj, form, change):
        if change and "status" in form.changed_data and obj.status in {"published", "rejected"}:
            if not self._can_review_news(request):
                raise PermissionDenied("You do not have permission to publish/reject news.")

        try:
            member_profile = request.user.member
            if not obj.pk:
                obj.created_by = member_profile
            obj.updated_by = member_profile
        except AttributeError:
            # Admin user without Member profile; leave fields as-is
            pass

        super().save_model(request, obj, form, change)

    class Media:
        css = {
            "all": ("admin_custom/news_changelist.css",)
        }

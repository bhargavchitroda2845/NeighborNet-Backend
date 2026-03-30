from django.contrib import admin
from django.db.models import Case, DateTimeField, F, IntegerField, Value, When
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect
from django.utils.html import format_html

from .models import BnsModel, Bid


@admin.register(BnsModel)
class BnsModelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "image_preview",
        "title",
        "status_badge",
        "listing_type",
        "contact",
        "area",
        "min_price",
        "max_price",
        "price",
        "bidding_enabled",
        "created_by_username",
        "published_at",
        "created_at",
    )
    # Exclude "sold" from admin panel filter - members can mark items as sold directly
    list_filter = ("listing_type", "bidding_enabled", "published_at", "created_at")
    list_per_page = 10
    list_max_show_all = 200
    search_fields = ("title", "contact", "desc", "area")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("image_preview", "created_at", "updated_at")
    sortable_by = ()

    def get_sortable_by(self, request):
        return ()

    def get_ordering(self, request):
        return (
            Case(
                When(status="inreview", then=Value(0)),
                When(status="rejected", then=Value(1)),
                When(status="published", then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            ),
            Case(
                When(status="inreview", then=F("updated_at")),
                When(status="published", then=Coalesce("published_at", "updated_at", "created_at")),
                default=F("updated_at"),
                output_field=DateTimeField(),
            ).desc(),
            F("id").desc(),
        )

    def changelist_view(self, request, extra_context=None):
        if "o" in request.GET:
            query = request.GET.copy()
            query.pop("o", None)
            qs = query.urlencode()
            redirect_url = request.path if not qs else f"{request.path}?{qs}"
            return HttpResponseRedirect(redirect_url)
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        return super().get_queryset(request)

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

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:4px;" />',
                obj.image.url,
            )
        return "-"

    image_preview.short_description = "Image"

    def save_model(self, request, obj, form, change):
        username = getattr(request.user, "username", None)
        member_profile = getattr(request.user, "member", None)

        if not obj.pk:
            obj.created_by_username = username
            if member_profile:
                obj.created_by = member_profile

        obj.updated_by_username = username
        if member_profile:
            obj.updated_by = member_profile

        super().save_model(request, obj, form, change)


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "item_title",
        "bidder_username",
        "bid_amount",
        "status_badge",
        "created_at",
    )
    list_filter = ("status", "created_at")
    list_per_page = 20
    search_fields = ("marketplace_item__title", "bidder__username", "message")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def item_title(self, obj):
        if obj.marketplace_item:
            return obj.marketplace_item.title
        return "-"
    item_title.short_description = "Item"

    def bidder_username(self, obj):
        if obj.bidder:
            return obj.bidder.username
        return "-"
    bidder_username.short_description = "Bidder"

    def status_badge(self, obj):
        color_map = {
            "pending": "#ffc107",
            "accepted": "#28a745",
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

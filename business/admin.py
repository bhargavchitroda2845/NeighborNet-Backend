from django.contrib import admin
from .models import Business, BusinessCategory


@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "icon", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "service", "location", "phone", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("name", "service", "location", "phone", "details")
    readonly_fields = ("id", "created_at", "updated_at", "published_at")
    ordering = ("-created_at",)
    
    fieldsets = (
        ("Basic Info", {
            "fields": ("id", "name", "slug", "category", "service", "location", "phone", "details")
        }),
        ("Additional Info", {
            "fields": ("image", "address", "area", "working_hours", "price_range_min", "price_range_max")
        }),
        ("Status", {
            "fields": ("status", "published_at")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "created_by", "updated_by")
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ("id",)
        return self.readonly_fields

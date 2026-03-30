from django.contrib import admin

from .models import Donation, DonationSubject, Expense


@admin.register(DonationSubject)
class DonationSubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_default", "is_active", "created_by", "created_at")
    list_filter = ("is_default", "is_active")
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        if not obj.created_by and request.user.is_authenticated:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        if obj.is_default:
            DonationSubject.objects.exclude(pk=obj.pk).update(is_default=False)
        elif not DonationSubject.objects.filter(is_default=True).exists():
            obj.is_default = True
            obj.save(update_fields=["is_default"])


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("id", "member", "name", "subject", "amount", "printed_by_name", "created_at")
    search_fields = ("name", "member__member_no", "member__first_name", "member__surname")
    list_filter = ("subject", "created_at")
    readonly_fields = ("printed_at", "printed_by_name")

    def save_model(self, request, obj, form, change):
        if not obj.created_by and request.user.is_authenticated:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "amount", "expense_date", "created_by")
    search_fields = ("title", "notes")
    list_filter = ("expense_date",)

    def save_model(self, request, obj, form, change):
        if not obj.created_by and request.user.is_authenticated:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

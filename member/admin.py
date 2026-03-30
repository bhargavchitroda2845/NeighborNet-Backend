from django.contrib import admin, messages
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from member.models import City, Country, Member, MemberDetail, MemberPasswordResetToken, State


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 50
    show_full_result_count = False

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "country")
    search_fields = ("name", "country__name")
    ordering = ("name",)
    list_select_related = ("country",)
    autocomplete_fields = ("country",)
    list_per_page = 50
    show_full_result_count = False

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "state", "country")
    search_fields = ("name", "state__name", "country__name")
    ordering = ("name",)
    list_select_related = ("country", "state")
    autocomplete_fields = ("country", "state")
    list_per_page = 50
    show_full_result_count = False

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    search_fields = ["member_no", "first_name", "middle_name", "surname", "email_id", "education", "username"]
    list_display = (
        "member_no",
        "first_name",
        "surname",
        "phone_no",
        "email_id",
        "approval_status",
        "status",
        "username",
        "country",
        "state",
        "city",
        "approved_by",
        "approved_at",
        "created_at",
    )
    list_filter = ("approval_status", "status", "gender")
    list_select_related = ("approved_by", "country", "state", "city")
    autocomplete_fields = ("country", "state", "city")
    readonly_fields = ("approved_by", "approved_at", "created_at", "updated_at")
    actions = ["approve_selected", "mark_not_approved"]
    list_per_page = 25
    list_max_show_all = 200
    show_full_result_count = False

    def _build_reset_link(self, token):
        path = reverse("member:reset_password_with_token", args=[token])
        base_url = getattr(settings, "SITE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        return f"{base_url}{path}"

    def _send_credentials_email(self, member, reset_link):
        if not member.email_id:
            return False, "Member email not available"

        subject = "Your Account Is Approved - Set Your Password"
        text_message = (
            f"Hello {member.first_name},\n\n"
            "Your account request has been approved.\n"
            f"Username: {member.username}\n"
            "For security, password is not sent in email.\n"
            "Use this one-time link to set your password:\n"
            f"{reset_link}\n\n"
            "This link will expire and can be used only once."
        )
        display_name = member.first_name or "Member"
        username = member.username or member.email_id or ""
        html_message = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Membership Approved</title>
</head>
<body style="margin:0;padding:0;background:#f2f3f5;font-family:Arial,sans-serif;color:#111;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:24px 12px;">
    <tr>
      <td align="center">
        <table width="700" cellpadding="0" cellspacing="0" style="max-width:700px;background:#ffffff;">
          <tr>
            <td style="background:#000;padding:28px 32px;color:#fff;">
              <div style="font-size:34px;font-weight:700;letter-spacing:1px;">Community Portal</div>
              <div style="font-size:12px;opacity:.85;margin-top:6px;">membership approval update</div>
            </td>
          </tr>
          <tr>
            <td style="padding:30px 32px;">
              <p style="margin:0 0 18px 0;font-size:18px;">Hello {display_name},</p>
              <p style="margin:0 0 18px 0;font-size:18px;line-height:1.6;">
                Your membership request has been <strong>approved</strong>.
              </p>
              <p style="margin:0 0 18px 0;font-size:18px;line-height:1.6;">
                <strong>Username:</strong> {username}<br>
                <strong>Password:</strong> Not shared by email for security.
              </p>
              <p style="margin:0 0 22px 0;font-size:18px;line-height:1.6;">
                Click below to set your password and activate your account.
              </p>
              <table cellpadding="0" cellspacing="0" style="margin:0 0 18px 0;">
                <tr>
                  <td bgcolor="#007bff" style="border-radius:4px;">
                    <a href="{reset_link}" style="display:inline-block;padding:12px 22px;color:#fff;text-decoration:none;font-size:14px;font-weight:700;">Set Password</a>
                  </td>
                </tr>
              </table>
              <p style="margin:0;font-size:13px;line-height:1.6;color:#555;">
                This link is one-time use and will expire automatically.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 32px;background:#f7f7f8;color:#666;font-size:12px;">
              &copy; 2026 Community Portal
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

        try:
            email = EmailMultiAlternatives(
                subject,
                text_message,
                settings.DEFAULT_FROM_EMAIL,
                [member.email_id],
                reply_to=[settings.REPLY_TO_EMAIL],
            )
            email.attach_alternative(html_message, "text/html")
            sent = email.send(fail_silently=False)
            if sent > 0:
                return True, None
            return False, "Email backend returned 0 sent emails"
        except Exception as exc:
            return False, f"{exc.__class__.__name__}: {exc}"

    def _approve_and_notify(self, member, approver):
        member.approve(approver=approver)
        ttl_minutes = int(getattr(settings, "PASSWORD_RESET_TOKEN_MINUTES", 30))
        token_obj = MemberPasswordResetToken.create_for_member(member, ttl_minutes=ttl_minutes)
        reset_link = self._build_reset_link(token_obj.token)
        sent, err = self._send_credentials_email(member, reset_link)
        return {
            "username": member.username,
            "set_password_link": reset_link,
            "email_sent": sent,
            "email_error": err,
        }

    @admin.action(description="Approve selected members and send credentials")
    def approve_selected(self, request, queryset):
        approved_count = 0
        email_count = 0
        email_errors = []
        for member in queryset:
            if member.approval_status == "Approved":
                continue
            result = self._approve_and_notify(member, request.user)
            approved_count += 1
            if result["email_sent"]:
                email_count += 1
            elif result["email_error"]:
                email_errors.append(
                    f"Member {member.member_no} ({member.email_id}): {result['email_error']}"
                )

        self.message_user(
            request,
            f"Approved {approved_count} member(s). Credentials email sent to {email_count} member(s).",
        )
        if email_errors:
            for err in email_errors[:5]:
                self.message_user(request, err, level=messages.ERROR)

    @admin.action(description="Mark selected members as Not Approved")
    def mark_not_approved(self, request, queryset):
        count = 0
        for member in queryset:
            member.mark_not_approved(approver=request.user)
            count += 1
        self.message_user(request, f"Marked {count} member(s) as Not Approved.")

    def save_model(self, request, obj, form, change):
        # If superadmin changes approval to Approved from change form,
        # generate credentials, save to DB, and send email immediately.
        if change and obj.pk:
            previous = Member.objects.filter(pk=obj.pk).values("approval_status").first()
            previous_status = previous["approval_status"] if previous else None
            if previous_status != "Approved" and obj.approval_status == "Approved":
                result = self._approve_and_notify(obj, request.user)
                self.message_user(
                    request,
                    (
                        "Member approved. "
                        f"Username: {result['username']} | "
                        f"Set Password Link: {result['set_password_link']}"
                    ),
                    level=messages.SUCCESS,
                )
                if not result["email_sent"] and result["email_error"]:
                    self.message_user(
                        request,
                        f"Credentials email failed: {result['email_error']}",
                        level=messages.ERROR,
                    )
                return

        super().save_model(request, obj, form, change)

    class Media:
        css = {
            "all": ("admin_custom/news_changelist.css",)
        }


@admin.register(MemberDetail)
class MemberDetailAdmin(admin.ModelAdmin):
    list_display = (
        "member_id",
        "member_no",
        "first_name",
        "surname",
        "age",
        "gender",
        "marital_status",
        "show_on_matrimonial",
        "is_matrimonial_public",
        "relation_with_member",
        "created_at",
    )
    list_filter = ("gender", "show_on_matrimonial", "is_matrimonial_public", "relation_with_member")
    readonly_fields = (
        "created_by",
        "created_at",
        "updated_by",
        "updated_at",
    )
    search_fields = (
        "first_name",
        "surname",
        "email_id",
        "education",
        "member_no__member_no",
        "member_no__first_name",
        "member_no__surname",
    )
    autocomplete_fields = ("member_no",)
    list_per_page = 25
    list_max_show_all = 200
    show_full_result_count = False
    actions = ["make_matrimonial_public", "make_matrimonial_private"]

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "member_no", "first_name", "middle_name", "surname",
                "date_of_birth", "age", "gender", "occupation",
                "email_id", "profile_image", "marital_status", "education",
            )
        }),
        ("Matrimonial Settings", {
            "classes": ("collapse",),
            "fields": (
                "show_on_matrimonial", "is_matrimonial_public", "relation_with_member",
                "height", "blood_group", "gotra", "manglik",
                "annual_income", "about_matrimonial", "matrimonial_photo",
            )
        }),
        ("Meta", {
            "classes": ("collapse",),
            "fields": ("created_by", "created_at", "updated_by", "updated_at"),
        }),
    )

    @admin.action(description="Make selected matrimonial profiles public")
    def make_matrimonial_public(self, request, queryset):
        updated = queryset.filter(show_on_matrimonial=True).update(is_matrimonial_public=True)
        self.message_user(request, f"{updated} profile(s) made public.")

    @admin.action(description="Hide selected matrimonial profiles from public")
    def make_matrimonial_private(self, request, queryset):
        updated = queryset.update(is_matrimonial_public=False)
        self.message_user(request, f"{updated} profile(s) hidden from public.")

    class Media:
        css = {
            "all": ("admin_custom/news_changelist.css",)
        }


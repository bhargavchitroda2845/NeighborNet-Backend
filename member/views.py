import json
from datetime import date

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .forms import MemberCreateForm, MemberDetailForm, MemberForm
from .models import City, Country, Member, MemberDetail, MemberPasswordResetToken, State, OTPVerification


def _abs_media_url(request, file_field):
    if not file_field:
        return None
    try:
        return request.build_absolute_uri(file_field.url)
    except Exception:
        return None


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _calc_age(dob):
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _build_reset_link(token, request=None):
    path = reverse("member:reset_password_with_token", args=[token])
    if request:
        return request.build_absolute_uri(path)
    base_url = getattr(settings, "SITE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return f"{base_url}{path}"


def _send_approval_email(member, reset_link):
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


def _send_request_received_email(member):
    if not member.email_id:
        return False, "Member email not available"

    subject = "Member Request Received"
    text_message = (
        f"Hello {member.first_name},\n\n"
        "Your membership request has been received successfully.\n"
        "Your account is currently Pending approval by superadmin.\n\n"
        "You will receive login credentials after approval."
    )
    display_name = member.first_name or "Member"
    html_message = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Member Request Received</title>
</head>
<body style="margin:0;padding:0;background:#f2f3f5;font-family:Arial,sans-serif;color:#111;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:24px 12px;">
    <tr>
      <td align="center">
        <table width="700" cellpadding="0" cellspacing="0" style="max-width:700px;background:#ffffff;">
          <tr>
            <td style="background:#000;padding:28px 32px;color:#fff;">
              <div style="font-size:34px;font-weight:700;letter-spacing:1px;">Community Portal</div>
              <div style="font-size:12px;opacity:.85;margin-top:6px;">membership request update</div>
            </td>
          </tr>
          <tr>
            <td style="padding:30px 32px;">
              <p style="margin:0 0 18px 0;font-size:18px;">Hello {display_name},</p>
              <p style="margin:0 0 18px 0;font-size:18px;line-height:1.6;">
                Your membership request has been received successfully.
              </p>
              <p style="margin:0 0 18px 0;font-size:18px;line-height:1.6;">
                Current status: <strong>Pending superadmin approval</strong>.
              </p>
              <p style="margin:0;font-size:14px;line-height:1.6;color:#555;">
                You will receive the next email after approval.
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
        sent = email.send(
            fail_silently=False,
        )
        if sent > 0:
            return True, None
        return False, "Email backend returned 0 sent emails"
    except Exception as exc:
        return False, f"{exc.__class__.__name__}: {exc}"


def _approve_member_and_send_email(member, approver, request=None):
    if member.approval_status == "Approved":
        return {
            "ok": False,
            "error": "Member already approved",
            "credentials": None,
            "email_sent": False,
            "email_error": None,
        }

    with transaction.atomic():
        member.approve(approver=approver)
        ttl_minutes = int(getattr(settings, "PASSWORD_RESET_TOKEN_MINUTES", 30))
        token_obj = MemberPasswordResetToken.create_for_member(member, ttl_minutes=ttl_minutes)
        reset_link = _build_reset_link(token_obj.token, request=request)

    email_sent, email_error = _send_approval_email(member, reset_link)
    return {
        "ok": True,
        "error": None,
        "credentials": {
            "username": member.username,
            "set_password_link": reset_link,
        },
        "email_sent": email_sent,
        "email_error": email_error,
    }


def _serialize_member(member, request):
    return {
        "member_no": member.member_no,
        "username": member.username,
        "first_name": member.first_name,
        "middle_name": member.middle_name,
        "surname": member.surname,
        "full_name": f"{member.first_name} {member.middle_name or ''} {member.surname}".strip(),
        "phone_no": member.phone_no,
        "email_id": member.email_id,
        "date_of_birth": member.date_of_birth.isoformat() if member.date_of_birth else None,
        "age": member.age,
        "gender": member.gender,
        "gender_label": member.get_gender_display(),
        "occupation": member.occupation,
        "country": {
            "id": member.country_id,
            "name": member.country.name if member.country else None,
        },
        "state": {
            "id": member.state_id,
            "name": member.state.name if member.state else None,
        },
        "city": {
            "id": member.city_id,
            "name": member.city.name if member.city else None,
        },
        "residential_address": member.residential_address,
        "marital_status": member.marital_status,
        "marital_status_label": member.get_marital_status_display() if member.marital_status else None,
        "education": member.education,
        "status": member.status,
        "approval_status": member.approval_status,
        "approved_at": member.approved_at.isoformat() if member.approved_at else None,
        "profile_image_url": _abs_media_url(request, member.profile_image),
        "created_at": member.created_at.isoformat() if member.created_at else None,
        "updated_at": member.updated_at.isoformat() if member.updated_at else None,
    }


def _serialize_member_detail(detail, request):
    if not detail:
        return None
    return {
        "member_id": detail.member_id,
        "first_name": detail.first_name,
        "middle_name": detail.middle_name,
        "surname": detail.surname,
        "full_name": f"{detail.first_name} {detail.middle_name or ''} {detail.surname}".strip(),
        "email_id": detail.email_id,
        "date_of_birth": detail.date_of_birth.isoformat() if detail.date_of_birth else None,
        "age": detail.age,
        "gender": detail.gender,
        "gender_label": detail.get_gender_display(),
        "occupation": detail.occupation,
        "marital_status": detail.marital_status,
        "marital_status_label": detail.get_marital_status_display() if detail.marital_status else None,
        "education": detail.education,
        "profile_image_url": _abs_media_url(request, detail.profile_image),
        "created_at": detail.created_at.isoformat() if detail.created_at else None,
        "updated_at": detail.updated_at.isoformat() if detail.updated_at else None,
    }


def get_logged_in_member(request):
    member_no = request.session.get("member_no")
    if not member_no:
        return None
    try:
        return Member.objects.get(member_no=member_no)
    except Member.DoesNotExist:
        return None


@csrf_exempt
def customer_login(request):
    print(f"DEBUG: customer_login - Method: {request.method}, Path: {request.path}")
    print(f"DEBUG: Content-Type: {request.content_type}")
    print(f"DEBUG: POST data: {dict(request.POST)}")
    
    if request.method == "POST":
        try:
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "")

            print(f"DEBUG: Login attempt - Username: {username}, Password received: {bool(password)}")

            if not username:
                return JsonResponse({"status": "error", "message": "Username is required"})
            
            if not password:
                return JsonResponse({"status": "error", "message": "Password is required"})

            try:
                member = Member.objects.get(username=username)
                print(f"DEBUG: Member found: {member.username}")

                if member.approval_status != "Approved":
                    return JsonResponse({"status": "error", "message": "Account is not approved yet"})

                if member.status != "Active":
                    return JsonResponse({"status": "error", "message": "Account is inactive"})

                if not member.password or not member.check_password(password):
                    print(f"DEBUG: Password check failed")
                    return JsonResponse({"status": "error", "message": "Invalid password"})

                request.session["member_no"] = member.member_no
                print(f"DEBUG: Login successful for {member.username}")
                
                # Return profile data directly in login response
                from marketplace.models import BnsModel
                from news.models import News
                
                details_qs = MemberDetail.objects.filter(member_no=member).order_by("-created_at")
                latest_detail = details_qs.first()
                latest_news = News.objects.filter(created_by=member).order_by("-created_at").first()
                latest_listing = BnsModel.objects.filter(created_by=member).order_by("-created_at").first()
                
                response_data = {
                    "status": "success",
                    "message": f"Welcome {member.username}",
                    "member": _serialize_member(member, request),
                    "counts": {
                        "details": details_qs.count(),
                        "news": News.objects.filter(created_by=member).count(),
                        "listings": BnsModel.objects.filter(created_by=member).count(),
                    },
                    "latest_detail": _serialize_member_detail(latest_detail, request),
                }
                return JsonResponse(response_data)

            except Member.DoesNotExist:
                print(f"DEBUG: Member not found: {username}")
                return JsonResponse({"status": "error", "message": "Username not found"})
                
        except Exception as e:
            print(f"DEBUG: Exception in login: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)})

    return render(request, "html_member/login.html")


def dashboard(request):
    member = get_logged_in_member(request)
    if not member:
        return redirect("member:customer_login")

    members = Member.objects.filter(member_no=member.member_no).annotate(detail_count=Count("details"))
    member_details = MemberDetail.objects.filter(member_no=member)

    context = {
        "member": member,
        "members": members,
        "member_details": member_details,
        "total_members": members.count(),
        "total_details": member_details.count(),
        "total_all": members.count() + member_details.count(),
    }

    return render(request, "html_member/dashboard.html", context)
def member_detail(request):
    member = get_logged_in_member(request)
    if not member:
        return redirect("member:customer_login")
    
    member_details = MemberDetail.objects.filter(member_no=member).order_by("-created_at")
    
    context = {
        "member": member,
        "member_details": member_details,
    }
    return render(request, "html_member/member_detail.html", context)




@csrf_exempt
@require_http_methods(["POST"])
def send_otp_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
        email = payload.get("email", "").strip().lower()
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON format"}, status=400)
    
    if not email:
        return JsonResponse({"detail": "Email is required"}, status=400)
    
    if Member.objects.filter(email_id__iexact=email).exclude(status="Blocked").exists():
        return JsonResponse({"detail": "A member with this email already exists"}, status=400)
    
    import secrets
    otp_code = "".join(str(secrets.randbelow(10)) for _ in range(6))
    
    OTPVerification.objects.create(email=email, otp_code=otp_code)
    
    from django.core.mail import send_mail
    subject = "Your Verification Code"
    message = f"Your verification code is: {otp_code}\nThis code will expire in 10 minutes."
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return JsonResponse({"status": "success", "message": "OTP sent successfully"})
    except Exception as e:
        return JsonResponse({"detail": f"Failed to send email: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def verify_otp_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
        email = payload.get("email", "").strip().lower()
        otp_code = payload.get("otp_code", "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON format"}, status=400)
    
    if not email or not otp_code:
        return JsonResponse({"detail": "Email and OTP code are required"}, status=400)
    
    otp_record = OTPVerification.objects.filter(email=email).order_by("-created_at").first()
    
    if not otp_record:
        return JsonResponse({"detail": "No OTP found for this email"}, status=400)
        
    if otp_record.is_verified:
        return JsonResponse({"detail": "OTP already verified"}, status=400)
    
    if otp_record.is_expired():
        return JsonResponse({"detail": "OTP has expired. Please request a new one"}, status=400)
        
    if otp_record.otp_code != otp_code:
        return JsonResponse({"detail": "Invalid OTP"}, status=400)
        
    otp_record.is_verified = True
    otp_record.save(update_fields=["is_verified"])
    
    return JsonResponse({"status": "success", "message": "Email verified successfully"})


def member_create_page(request):
    form = MemberCreateForm()
    return render(request, "html_member/member_create.html", {"form": form})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def member_create_api(request):
    if request.method == "GET":
        return JsonResponse(
            {
                "detail": "Use POST to create member",
                "required_fields": [
                    "first_name",
                    "surname",
                    "phone_no",
                    "email_id",
                    "gender",
                    "country",
                    "state",
                    "residential_address",
                ],
                "optional_fields": [
                    "middle_name",
                    "date_of_birth",
                    "occupation",
                    "city",
                ],
            }
        )

    if request.content_type and "application/json" in request.content_type:
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON payload"}, status=400)
        form = MemberCreateForm(payload)
    else:
        form = MemberCreateForm(request.POST)

    if not form.is_valid():
        return JsonResponse({"status": "error", "errors": form.errors}, status=400)

    cleaned = form.cleaned_data
    
    email_id = cleaned.get("email_id")
    if email_id:
        email_id = email_id.lower()
        otp_record = OTPVerification.objects.filter(email=email_id, is_verified=True).order_by("-created_at").first()
        if not otp_record:
            return JsonResponse({"status": "error", "message": "Email address must be verified before registration."}, status=400)
    else:
        return JsonResponse({"status": "error", "message": "Email address is required and must be verified."}, status=400)

    member = form.save(commit=False)
    member.age = _calc_age(cleaned.get("date_of_birth"))
    member.status = "Inactive"
    member.approval_status = "Pending"
    member.username = None
    member.password = None

    logged_in_member = get_logged_in_member(request)
    if logged_in_member and logged_in_member.user:
        member.created_by = logged_in_member.user
        member.updated_by = logged_in_member.user

    member.save()
    request_email_sent, request_email_error = _send_request_received_email(member)

    return JsonResponse(
        {
            "status": "success",
            "message": "Member request submitted. Waiting for superadmin approval.",
            "member": _serialize_member(member, request),
            "request_email_sent": request_email_sent,
            "request_email_error": request_email_error,
        },
        status=201,
    )


def _require_superadmin(request):
    return request.user.is_authenticated and request.user.is_superuser


@require_GET
def pending_member_requests_api(request):
    if not _require_superadmin(request):
        return JsonResponse({"detail": "Superadmin access required"}, status=403)

    qs = Member.objects.filter(approval_status="Pending").order_by("-created_at")
    data = [_serialize_member(member, request) for member in qs]
    return JsonResponse({"results": data, "count": len(data)})


@csrf_exempt
@require_http_methods(["POST"])
def approve_member_api(request, member_no):
    if not _require_superadmin(request):
        return JsonResponse({"detail": "Superadmin access required"}, status=403)

    member = Member.objects.filter(member_no=member_no).first()
    if not member:
        return JsonResponse({"detail": "Member not found"}, status=404)

    result = _approve_member_and_send_email(member, request.user, request=request)
    if not result["ok"]:
        return JsonResponse({"detail": result["error"]}, status=400)

    return JsonResponse(
        {
            "status": "success",
            "message": "Member approved successfully",
            "member": _serialize_member(member, request),
            "credentials": result["credentials"],
            "email_sent": result["email_sent"],
            "email_error": result["email_error"],
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def reject_member_api(request, member_no):
    if not _require_superadmin(request):
        return JsonResponse({"detail": "Superadmin access required"}, status=403)

    member = Member.objects.filter(member_no=member_no).first()
    if not member:
        return JsonResponse({"detail": "Member not found"}, status=404)

    member.mark_not_approved(approver=request.user)
    return JsonResponse({"status": "success", "message": "Member marked as not approved"})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def reset_password_with_token(request, token):
    token_obj = (
        MemberPasswordResetToken.objects.select_related("member")
        .filter(token=token)
        .first()
    )

    if not token_obj:
        return render(
            request,
            "html_member/reset_password.html",
            {"invalid": True, "message": "Invalid reset link."},
            status=400,
        )

    if not token_obj.is_valid():
        return render(
            request,
            "html_member/reset_password.html",
            {"invalid": True, "message": "Reset link is expired or already used."},
            status=400,
        )

    if request.method == "POST":
        password = (request.POST.get("password") or "").strip()
        confirm_password = (request.POST.get("confirm_password") or "").strip()

        if len(password) < 8:
            return render(
                request,
                "html_member/reset_password.html",
                {"invalid": False, "message": "Password must be at least 8 characters."},
                status=400,
            )

        if password != confirm_password:
            return render(
                request,
                "html_member/reset_password.html",
                {"invalid": False, "message": "Passwords do not match."},
                status=400,
            )

        member = token_obj.member
        member.set_password(password)
        token_obj.mark_used()
        return render(
            request,
            "html_member/reset_password.html",
            {"success": True, "message": "Password set successfully. You can now login."},
        )

    return render(
        request,
        "html_member/reset_password.html",
        {"invalid": False, "message": ""},
    )

@require_GET
def country_list_api(request):
    countries = list(Country.objects.values("id", "name").order_by("name"))
    return JsonResponse({"results": countries})


@require_GET
def state_list_api(request):
    country_id = _safe_int(request.GET.get("country_id"))

    qs = State.objects.select_related("country").all()
    if country_id:
        if not Country.objects.filter(id=country_id).exists():
            return JsonResponse({"detail": "country_id not found"}, status=404)
        qs = qs.filter(country_id=country_id)

    data = [
        {
            "id": st.id,
            "name": st.name,
            "country_id": st.country_id,
            "country_name": st.country.name if st.country else None,
        }
        for st in qs.order_by("name")
    ]
    return JsonResponse({"results": data, "count": len(data)})


@require_GET
def city_list_api(request):
    country_id = _safe_int(request.GET.get("country_id"))
    state_id = _safe_int(request.GET.get("state_id"))

    state_obj = None
    if state_id:
        state_obj = State.objects.select_related("country").filter(id=state_id).first()
        if not state_obj:
            return JsonResponse({"detail": "state_id not found"}, status=404)

    if country_id:
        if not Country.objects.filter(id=country_id).exists():
            return JsonResponse({"detail": "country_id not found"}, status=404)

    if state_obj and country_id and state_obj.country_id != country_id:
        return JsonResponse({"detail": "state_id does not belong to country_id"}, status=400)

    qs = City.objects.select_related("country", "state").all()
    if state_obj:
        qs = qs.filter(state_id=state_obj.id)
    elif country_id:
        qs = qs.filter(country_id=country_id)

    data = [
        {
            "id": city.id,
            "name": city.name,
            "country_id": city.country_id,
            "country_name": city.country.name if city.country else None,
            "state_id": city.state_id,
            "state_name": city.state.name if city.state else None,
        }
        for city in qs.order_by("name")
    ]
    return JsonResponse({"results": data, "count": len(data)})


@require_GET
def location_relation_api(request):
    country_id = _safe_int(request.GET.get("country_id"))
    state_id = _safe_int(request.GET.get("state_id"))

    state_obj = None
    if state_id:
        state_obj = State.objects.select_related("country").filter(id=state_id).first()
        if not state_obj:
            return JsonResponse({"detail": "state_id not found"}, status=404)

    if state_obj and country_id and state_obj.country_id != country_id:
        return JsonResponse({"detail": "state_id does not belong to country_id"}, status=400)

    country_qs = Country.objects.all()
    if country_id:
        country_qs = country_qs.filter(id=country_id)
        if not country_qs.exists():
            return JsonResponse({"detail": "country_id not found"}, status=404)
    if state_obj:
        country_qs = country_qs.filter(id=state_obj.country_id)

    countries = list(country_qs.order_by("name").values("id", "name"))
    if not countries:
        return JsonResponse({"results": [], "count": 0})

    country_ids = [item["id"] for item in countries]
    state_qs = State.objects.filter(country_id__in=country_ids)
    if state_obj:
        state_qs = state_qs.filter(id=state_obj.id)
    states = list(
        state_qs
        .order_by("name")
        .values("id", "name", "country_id")
    )
    city_qs = City.objects.filter(country_id__in=country_ids)
    if state_obj:
        city_qs = city_qs.filter(state_id=state_obj.id)
    cities = list(
        city_qs
        .order_by("name")
        .values("id", "name", "country_id", "state_id")
    )

    states_by_country = {}
    for st in states:
        states_by_country.setdefault(st["country_id"], []).append(
            {"id": st["id"], "name": st["name"], "cities": []}
        )

    cities_without_state_by_country = {}
    for city in cities:
        city_data = {"id": city["id"], "name": city["name"]}
        if city["state_id"]:
            for st in states_by_country.get(city["country_id"], []):
                if st["id"] == city["state_id"]:
                    st["cities"].append(city_data)
                    break
        else:
            cities_without_state_by_country.setdefault(city["country_id"], []).append(city_data)

    results = []
    for c in countries:
        results.append(
            {
                "id": c["id"],
                "name": c["name"],
                "states": states_by_country.get(c["id"], []),
                "cities_without_state": cities_without_state_by_country.get(c["id"], []),
            }
        )

    return JsonResponse({"results": results, "count": len(results)})


def member_detail_add(request):
    member = get_logged_in_member(request)
    if not member:
        return redirect("member:customer_login")

    if request.method == "POST":
        form = MemberDetailForm(request.POST, request.FILES)

        if form.is_valid():
            member_detail = form.save(commit=False)
            member_detail.member_no = member
            member_detail.created_by = member
            member_detail.updated_by = member
            member_detail.save()

            return JsonResponse({"status": "success", "message": "Member detail saved successfully"})

        return JsonResponse({"status": "error", "errors": form.errors})

    form = MemberDetailForm()
    return render(request, "html_member/member_detail_add.html", {"form": form, "member": member})


def member_edit(request):
    member = get_logged_in_member(request)
    if not member:
        return redirect("member:customer_login")

    if request.method == "POST":
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = member.user if member.user else None
            obj.save()
            return redirect("member:profile")
    else:
        form = MemberForm(instance=member)

    return render(request, "html_member/member_edit.html", {"form": form, "member": member})


def member_detail_edit(request, member_id):
    member = get_logged_in_member(request)
    if not member:
        return redirect("member:customer_login")

    try:
        member_detail = MemberDetail.objects.get(member_id=member_id, member_no=member)
    except MemberDetail.DoesNotExist:
        return redirect("member:dashboard")

    if request.method == "POST":
        form = MemberDetailForm(request.POST, request.FILES, instance=member_detail)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = member
            obj.save()
            return redirect("member:profile")
        else:
            print("MEMBER DETAIL EDIT FORM ERRORS:", form.errors)
    else:
        form = MemberDetailForm(instance=member_detail)

    return render(
        request,
        "html_member/member_detail_edit.html",
        {
            "form": form,
            "member": member,
            "member_detail": member_detail,
        },
    )


def profile(request):
    member = get_logged_in_member(request)
    if not member:
        return redirect("member:customer_login")

    from marketplace.models import BnsModel
    from news.models import News

    member_details_qs = MemberDetail.objects.filter(member_no=member)
    latest_detail = member_details_qs.order_by("-created_at").first()
    latest_news = News.objects.filter(created_by=member).order_by("-created_at").first()
    latest_listing = BnsModel.objects.filter(created_by=member).order_by("-created_at").first()

    return render(
        request,
        "html_member/profile.html",
        {
            "member": member,
            "detail_count": member_details_qs.count(),
            "news_count": News.objects.filter(created_by=member).count(),
            "listing_count": BnsModel.objects.filter(created_by=member).count(),
            "latest_detail": latest_detail,
            "latest_news": latest_news,
            "latest_listing": latest_listing,
        },
    )


@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def profile_api(request):
    if request.method == "OPTIONS":
        return JsonResponse({"status": "ok"})
    
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    member = get_logged_in_member(request)
    print(f"DEBUG: Profile API - Member session: {request.session.get('member_no')}, Member: {member}")
    
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    from marketplace.models import BnsModel
    from news.models import News

    details_qs = MemberDetail.objects.filter(member_no=member).order_by("-created_at")
    latest_detail = details_qs.first()
    latest_news = News.objects.filter(created_by=member).order_by("-created_at").first()
    latest_listing = BnsModel.objects.filter(created_by=member).order_by("-created_at").first()

    response = {
        "member": _serialize_member(member, request),
        "counts": {
            "details": details_qs.count(),
            "news": News.objects.filter(created_by=member).count(),
            "listings": BnsModel.objects.filter(created_by=member).count(),
        },
        "latest_detail": _serialize_member_detail(latest_detail, request),
        "latest_news": {
            "id": latest_news.id,
            "title": latest_news.title,
            "slug": latest_news.slug,
            "status": latest_news.status,
            "status_label": latest_news.get_status_display(),
            "category": latest_news.category.name if latest_news.category else None,
            "created_at": latest_news.created_at.isoformat() if latest_news.created_at else None,
        }
        if latest_news
        else None,
        "latest_listing": {
            "id": latest_listing.id,
            "title": latest_listing.title,
            "slug": latest_listing.slug,
            "status": latest_listing.status,
            "status_label": latest_listing.get_status_display(),
            "listing_type": latest_listing.listing_type,
            "listing_type_label": latest_listing.get_listing_type_display(),
            "price": latest_listing.price,
            "created_at": latest_listing.created_at.isoformat() if latest_listing.created_at else None,
            "image_url": _abs_media_url(request, latest_listing.image),
        }
        if latest_listing
        else None,
    }
    print(f"DEBUG: Profile API returning data for member {member.member_no}")
    return JsonResponse(response)


def public_profile_api(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    member_no = (request.GET.get("member_no") or "").strip()
    username = (request.GET.get("username") or "").strip()

    if not member_no and not username:
        return JsonResponse({"detail": "Pass member_no or username as query parameter"}, status=400)

    qs = Member.objects.all()
    if member_no:
        qs = qs.filter(member_no=member_no)
    else:
        qs = qs.filter(username=username)

    member = qs.first()
    if not member:
        return JsonResponse({"detail": "Member not found"}, status=404)

    data = {
        "member_no": member.member_no,
        "first_name": member.first_name,
        "middle_name": member.middle_name,
        "surname": member.surname,
        "full_name": f"{member.first_name} {member.middle_name or ''} {member.surname}".strip(),
        "email_id": member.email_id,
        "gender": member.gender,
        "gender_label": member.get_gender_display(),
        "occupation": member.occupation,
        "country": {
            "id": member.country_id,
            "name": member.country.name if member.country else None,
        },
        "state": {
            "id": member.state_id,
            "name": member.state.name if member.state else None,
        },
        "city": {
            "id": member.city_id,
            "name": member.city.name if member.city else None,
        },
        "residential_address": member.residential_address,
        "marital_status": member.marital_status,
        "marital_status_label": member.get_marital_status_display() if member.marital_status else None,
        "education": member.education,
        "profile_image_url": _abs_media_url(request, member.profile_image),
    }
    return JsonResponse({"result": data})


def memberjson(request):
    return render(request, "html_member/member.json")


@csrf_exempt
def logout_view(request):
    request.session.flush()
    return render(request, "html_member/login.html")


@require_GET
def matrimonial_list_api(request):
    """Public API: returns all matrimonial profiles that are active & public."""
    qs = MemberDetail.objects.filter(
        show_on_matrimonial=True,
        is_matrimonial_public=True,
        age__gte=18,
    ).select_related("member_no").order_by("-created_at")

    is_logged_in = request.GET.get("logged_in") == "true"
    if not is_logged_in:
        qs = qs.exclude(matrimonial_visibility="Protected")

    results = []
    for d in qs:
        results.append({
            "id": d.member_id,
            "first_name": d.first_name,
            "middle_name": d.middle_name or "",
            "surname": d.surname,
            "full_name": f"{d.first_name} {d.middle_name or ''} {d.surname}".strip(),
            "age": d.age,
            "gender": d.gender,
            "gender_label": d.get_gender_display(),
            "date_of_birth": d.date_of_birth.isoformat() if d.date_of_birth else None,
            "occupation": d.occupation,
            "education": d.education,
            "marital_status": d.marital_status,
            "marital_status_label": d.get_marital_status_display() if d.marital_status else None,
            "relation_with_member": d.relation_with_member,
            "relation_label": d.get_relation_with_member_display() if d.relation_with_member else None,
            "height": d.height,
            "blood_group": d.blood_group,
            "gotra": d.gotra,
            "manglik": d.manglik,
            "manglik_label": d.get_manglik_display() if d.manglik else None,
            "annual_income": d.annual_income,
            "about_matrimonial": d.about_matrimonial,
            "matrimonial_photo_url": _abs_media_url(request, d.matrimonial_photo),
            "profile_image_url": _abs_media_url(request, d.profile_image),
            # Extended fields
            "diet": d.diet,
            "diet_label": d.get_diet_display() if d.diet else None,
            "addictions": d.addictions,
            "father_name": d.father_name,
            "mother_name": d.mother_name,
            "family_type": d.family_type,
            "family_type_label": d.get_family_type_display() if d.family_type else None,
            "siblings": d.siblings,
            "contact_phone": d.contact_phone,
            "full_bio": d.full_bio,
            "hobbies": d.hobbies,
            "partner_preference": d.partner_preference,
            # Location from the primary member
            "city": d.member_no.city.name if d.member_no.city else None,
            "state": d.member_no.state.name if d.member_no.state else None,
            "country": d.member_no.country.name if d.member_no.country else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    return JsonResponse({"results": results, "count": len(results)})


@csrf_exempt
@require_http_methods(["POST"])
def matrimonial_toggle_public(request, member_id):
    """Logged-in member can toggle public/private for their own matrimonial detail."""
    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    try:
        detail = MemberDetail.objects.get(member_id=member_id, member_no=member)
    except MemberDetail.DoesNotExist:
        return JsonResponse({"detail": "Not found"}, status=404)

    if not detail.show_on_matrimonial:
        return JsonResponse({"detail": "This profile is not enabled for matrimonial."}, status=400)

    detail.is_matrimonial_public = not detail.is_matrimonial_public
    detail.save(update_fields=["is_matrimonial_public", "updated_at"])
    return JsonResponse({
        "status": "success",
        "is_matrimonial_public": detail.is_matrimonial_public,
        "message": "Profile is now public." if detail.is_matrimonial_public else "Profile is now private.",
    })


@require_GET
def matrimonial_detail_api(request, member_id):
    """Public API: returns a single public matrimonial profile by member_detail ID."""
    try:
        d = MemberDetail.objects.select_related("member_no").get(
            member_id=member_id,
            show_on_matrimonial=True,
            is_matrimonial_public=True,
            age__gte=18,
        )
    except MemberDetail.DoesNotExist:
        return JsonResponse({"detail": "Profile not found"}, status=404)

    data = {
        "id": d.member_id,
        "first_name": d.first_name,
        "middle_name": d.middle_name or "",
        "surname": d.surname,
        "full_name": f"{d.first_name} {d.middle_name or ''} {d.surname}".strip(),
        "age": d.age,
        "date_of_birth": d.date_of_birth.isoformat() if d.date_of_birth else None,
        "gender": d.gender,
        "gender_label": d.get_gender_display(),
        "occupation": d.occupation,
        "education": d.education,
        "marital_status": d.marital_status,
        "marital_status_label": d.get_marital_status_display() if d.marital_status else None,
        "relation_with_member": d.relation_with_member,
        "relation_label": d.get_relation_with_member_display() if d.relation_with_member else None,
        "height": d.height,
        "blood_group": d.blood_group,
        "gotra": d.gotra,
        "manglik": d.manglik,
        "manglik_label": d.get_manglik_display() if d.manglik else None,
        "annual_income": d.annual_income,
        "about_matrimonial": d.about_matrimonial,
        "matrimonial_photo_url": _abs_media_url(request, d.matrimonial_photo),
        "profile_image_url": _abs_media_url(request, d.profile_image),
        # Extended fields
        "diet": d.diet,
        "diet_label": d.get_diet_display() if d.diet else None,
        "addictions": d.addictions,
        "father_name": d.father_name,
        "mother_name": d.mother_name,
        "family_type": d.family_type,
        "family_type_label": d.get_family_type_display() if d.family_type else None,
        "siblings": d.siblings,
        "contact_phone": d.contact_phone,
        "full_bio": d.full_bio,
        "hobbies": d.hobbies,
        "partner_preference": d.partner_preference,
        "city": d.member_no.city.name if d.member_no.city else None,
        "state": d.member_no.state.name if d.member_no.state else None,
        "country": d.member_no.country.name if d.member_no.country else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }
    return JsonResponse({"result": data})


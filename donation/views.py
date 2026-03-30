from io import BytesIO
from decimal import Decimal

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from member.models import Member

from .forms import DonationForm
from .models import Donation


def _session_member(request):
    member_no = request.session.get("member_no")
    if not member_no:
        return None
    return Member.objects.filter(
        member_no=member_no,
        approval_status="Approved",
        status="Active",
    ).first()


def _member_payload(member):
    return {
        "member_no": member.member_no,
        "name": f"{member.first_name} {member.middle_name or ''} {member.surname}".strip(),
        "address": member.residential_address or "",
        "city": member.city.name if member.city else "",
        "state": member.state.name if member.state else "",
        "country": member.country.name if member.country else "",
    }


def _display_user(user):
    if not user or not user.is_authenticated:
        return ""
    full_name = (user.get_full_name() or "").strip()
    return full_name or user.username


def _is_superadmin(user):
    return user.is_authenticated and user.is_superuser


def _number_to_words(n):
    ones = [
        "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen",
    ]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    if n < 20:
        return ones[n]
    if n < 100:
        return tens[n // 10] + ("" if n % 10 == 0 else f" {ones[n % 10]}")
    if n < 1000:
        return ones[n // 100] + " Hundred" + ("" if n % 100 == 0 else f" {_number_to_words(n % 100)}")
    if n < 1_000_000:
        return _number_to_words(n // 1000) + " Thousand" + ("" if n % 1000 == 0 else f" {_number_to_words(n % 1000)}")
    if n < 1_000_000_000:
        return _number_to_words(n // 1_000_000) + " Million" + ("" if n % 1_000_000 == 0 else f" {_number_to_words(n % 1_000_000)}")
    return _number_to_words(n // 1_000_000_000) + " Billion" + ("" if n % 1_000_000_000 == 0 else f" {_number_to_words(n % 1_000_000_000)}")


def _amount_to_words(amount):
    value = Decimal(amount).quantize(Decimal("0.01"))
    whole = int(value)
    fraction = int((value - whole) * 100)
    whole_text = _number_to_words(whole) + " Rupees"
    if fraction:
        return f"{whole_text} and {_number_to_words(fraction)} Paisa Only"
    return f"{whole_text} Only"


@require_GET
def member_prefill_api(request):
    member_no = request.GET.get("member_no")
    member = None

    if member_no:
        try:
            member_no = int(member_no)
        except ValueError:
            return JsonResponse({"status": "error", "message": "Invalid member number"}, status=400)
        member = Member.objects.filter(
            member_no=member_no,
            approval_status="Approved",
            status="Active",
        ).first()
    else:
        member = _session_member(request)

    if not member:
        return JsonResponse({"status": "error", "message": "Member not found"}, status=404)

    return JsonResponse({"status": "success", "member": _member_payload(member)})


def donation_create(request):
    session_member = _session_member(request)

    if request.method == "POST":
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)

            posted_member_no = form.cleaned_data.get("member_no")
            target_member = (
                Member.objects.filter(
                    member_no=posted_member_no,
                    approval_status="Approved",
                    status="Active",
                ).first()
                if posted_member_no
                else session_member
            )

            if not target_member:
                form.add_error("member_no", "Member number is required or login session must exist.")
            else:
                donation.member = target_member
                if request.user.is_authenticated:
                    donation.created_by = request.user

                defaults = _member_payload(target_member)
                donation.name = donation.name or defaults["name"]
                donation.address = donation.address or defaults["address"]
                donation.city = donation.city or defaults["city"]
                donation.state = donation.state or defaults["state"]
                donation.country = donation.country or defaults["country"]
                donation.amount_in_words = _amount_to_words(donation.amount)
                donation.save()

                if request.POST.get("action") == "download":
                    return redirect(reverse("donation:donation_pdf", args=[donation.id]))

                form = DonationForm(initial={
                    "member_no": target_member.member_no,
                    "name": donation.name,
                    "address": donation.address,
                    "city": donation.city,
                    "state": donation.state,
                    "country": donation.country,
                    "subject": donation.subject_id,
                    "amount": donation.amount,
                })
                return render(
                    request,
                    "html_donation/donation_form.html",
                    {
                        "form": form,
                        "member": session_member,
                        "saved_donation": donation,
                        "success_message": "Donation saved successfully.",
                    },
                )
    else:
        initial = {}
        if session_member:
            initial.update(_member_payload(session_member))
            initial["member_no"] = session_member.member_no
        form = DonationForm(initial=initial)

    return render(
        request,
        "html_donation/donation_form.html",
        {
            "form": form,
            "member": session_member,
        },
    )


def donation_pdf(request, donation_id):
    donation = Donation.objects.select_related("member", "subject", "created_by").filter(id=donation_id).first()
    if not donation:
        return HttpResponse("Donation not found", status=404)

    session_member = _session_member(request)
    is_owner = session_member and session_member.member_no == donation.member_id
    is_superadmin = _is_superadmin(request.user)

    if not is_owner and not is_superadmin:
        return HttpResponse("Not allowed", status=403)

    if session_member:
        member_label = f"Member No {session_member.member_no}"
        donation.printed_by_name = member_label
    elif request.user.is_authenticated:
        donation.printed_by_name = _display_user(request.user)
    else:
        donation.printed_by_name = "System"

    if not donation.created_by and request.user.is_authenticated:
        donation.created_by = request.user

    donation.printed_at = timezone.now()
    donation.save(update_fields=["printed_by_name", "printed_at", "created_by", "updated_at"])

    try:
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except Exception:
        return HttpResponse("PDF library not installed. Run: pip install reportlab", status=500, content_type="text/plain")

    labels = {
        "title": "DONATION VOUCHER",
        "voucher_no": "Voucher No",
        "date": "Date",
        "member_no": "Member No",
        "name": "Name",
        "address": "Address",
        "city": "City",
        "state": "State",
        "country": "Country",
        "amount_words": "Amount (Words)",
        "amount": "Amount",
        "subject": "Subjected To",
        "printed_by": "Printed By",
        "printed_at": "Printed At",
        "sign_president": "Signature (President)",
        "sign_secretary": "Signature (Secretary)",
        "sign_member": "Signature (Member)",
    }

    font_regular = "Helvetica"
    font_bold = "Helvetica-Bold"

    def register_font(font_name, file_name):
        from pathlib import Path

        full_path = Path(settings.BASE_DIR) / "static" / "fonts" / file_name
        if full_path.exists():
            pdfmetrics.registerFont(TTFont(font_name, str(full_path)))
            return True
        return False

    if register_font("NotoSansGujarati", "NotoSansGujarati-Regular.ttf"):
        font_regular = "NotoSansGujarati"
        font_bold = "NotoSansGujarati"

    page_width = 7 * inch
    page_height = 4 * inch
    cbuf = BytesIO()
    c = canvas.Canvas(cbuf, pagesize=(page_width, page_height))

    stroke = colors.HexColor("#58aac8")
    heading = colors.HexColor("#d3177f")
    label_color = colors.HexColor("#1889b2")

    def fit_text(value, max_width, font_name, size):
        value = str(value or "")
        if pdfmetrics.stringWidth(value, font_name, size) <= max_width:
            return value
        suffix = "..."
        while value and pdfmetrics.stringWidth(value + suffix, font_name, size) > max_width:
            value = value[:-1]
        return value + suffix if value else ""

    def hline(x1, x2, y, lw=0.8):
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
        c.line(x1, y, x2, y)

    def vline(x, y1, y2, lw=0.8):
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
        c.line(x, y1, x, y2)

    def txt(x, y, value, size=8, color=label_color, bold=False):
        c.setFillColor(color)
        c.setFont(font_bold if bold else font_regular, size)
        c.drawString(x, y, str(value or ""))

    x0 = 0.18 * inch
    y0 = 0.18 * inch
    w = 6.64 * inch
    h = 3.64 * inch

    c.setStrokeColor(stroke)
    c.setLineWidth(1)
    c.roundRect(x0, y0, w, h, 4, stroke=1, fill=0)

    y_top = y0 + h

    hline(x0, x0 + w, y_top - 0.45 * inch)
    vline(x0 + w - 2.10 * inch, y_top, y_top - 0.45 * inch)

    txt(x0 + w - 2.0 * inch, y_top - 0.24 * inch, labels["title"], size=11, color=heading, bold=True)
    txt(x0 + w - 2.03 * inch, y_top - 0.38 * inch, f"{labels['voucher_no']}: {donation.id}", size=7)
    txt(x0 + w - 2.03 * inch, y_top - 0.50 * inch, f"{labels['date']}: {timezone.localdate().isoformat()}", size=7)

    row1 = y_top - 0.75 * inch
    txt(x0 + 0.05 * inch, row1 + 0.08 * inch, labels["member_no"], size=7)
    hline(x0 + 0.55 * inch, x0 + 1.75 * inch, row1)
    txt(x0 + 0.58 * inch, row1 + 0.03 * inch, donation.member_id, size=8, color=colors.black)

    txt(x0 + 1.88 * inch, row1 + 0.08 * inch, labels["name"], size=7)
    hline(x0 + 2.20 * inch, x0 + w - 0.08 * inch, row1)
    txt(x0 + 2.24 * inch, row1 + 0.03 * inch, fit_text(donation.name, 4.4 * inch, font_regular, 8), size=8, color=colors.black)

    row2 = y_top - 1.05 * inch
    txt(x0 + 0.05 * inch, row2 + 0.08 * inch, labels["address"], size=7)
    hline(x0 + 0.43 * inch, x0 + w - 0.08 * inch, row2)
    txt(x0 + 0.47 * inch, row2 + 0.03 * inch, fit_text(donation.address, 6.0 * inch, font_regular, 8), size=8, color=colors.black)

    row3 = y_top - 1.35 * inch
    txt(x0 + 0.05 * inch, row3 + 0.08 * inch, labels["city"], size=7)
    hline(x0 + 0.24 * inch, x0 + 1.65 * inch, row3)
    txt(x0 + 0.27 * inch, row3 + 0.03 * inch, fit_text(donation.city, 1.3 * inch, font_regular, 8), size=8, color=colors.black)

    txt(x0 + 1.82 * inch, row3 + 0.08 * inch, labels["state"], size=7)
    hline(x0 + 2.08 * inch, x0 + 3.60 * inch, row3)
    txt(x0 + 2.12 * inch, row3 + 0.03 * inch, fit_text(donation.state, 1.4 * inch, font_regular, 8), size=8, color=colors.black)

    txt(x0 + 3.80 * inch, row3 + 0.08 * inch, labels["country"], size=7)
    hline(x0 + 4.20 * inch, x0 + w - 0.08 * inch, row3)
    txt(x0 + 4.24 * inch, row3 + 0.03 * inch, fit_text(donation.country, 2.35 * inch, font_regular, 8), size=8, color=colors.black)

    table_top = y_top - 1.65 * inch
    table_bottom = y_top - 2.62 * inch

    hline(x0, x0 + w, table_top)
    hline(x0, x0 + w, table_bottom)
    vline(x0, table_top, table_bottom)
    vline(x0 + 4.8 * inch, table_top, table_bottom)
    vline(x0 + w, table_top, table_bottom)

    hline(x0, x0 + w, table_top - 0.23 * inch)
    hline(x0, x0 + w, table_top - 0.50 * inch)

    txt(x0 + 0.08 * inch, table_top - 0.17 * inch, labels["amount_words"], size=7, bold=True)
    txt(x0 + 4.88 * inch, table_top - 0.17 * inch, labels["amount"], size=7, bold=True)

    txt(x0 + 0.08 * inch, table_top - 0.44 * inch, fit_text(donation.amount_in_words, 4.6 * inch, font_regular, 8), size=8, color=colors.black)
    txt(x0 + 4.88 * inch, table_top - 0.44 * inch, f"{donation.amount:.2f}", size=8, color=colors.black)
    txt(x0 + 0.08 * inch, table_top - 0.71 * inch, f"{labels['subject']}: {fit_text(donation.subject.name, 5.9 * inch, font_regular, 8)}", size=8, color=colors.black)

    meta_y = y_top - 2.92 * inch
    txt(x0 + 0.08 * inch, meta_y, f"{labels['printed_by']}: {donation.printed_by_name or '-'}", size=7, color=colors.black)
    printed_at = donation.printed_at.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%d %H:%M:%S") if donation.printed_at else "-"
    txt(x0 + 3.55 * inch, meta_y, f"{labels['printed_at']}: {printed_at}", size=7, color=colors.black)

    sign_y = y_top - 3.16 * inch
    txt(x0 + 1.15 * inch, sign_y, labels["sign_president"], size=7)
    txt(x0 + 3.15 * inch, sign_y, labels["sign_secretary"], size=7)
    txt(x0 + 5.10 * inch, sign_y, labels["sign_member"], size=7)

    c.showPage()
    c.save()

    cbuf.seek(0)
    filename = f"donation-voucher-{donation.id}.pdf"
    response = HttpResponse(cbuf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response



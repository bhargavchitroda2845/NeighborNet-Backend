from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
import os

from .models import Business, BusinessCategory
from member.models import Member

STATUS_CODE_MAP = {
    "inreview": 0,
    "published": 1,
    "rejected": 2,
    "draft": 3,
}


def _business_image_name(business_pk, original_name):
    ext = os.path.splitext(original_name or "")[1].lower() or ".jpg"
    return f"image{business_pk}{ext}"


def _public_media_url(file_url, request=None):
    # Return absolute URL for media files
    # Try to get base from request, fallback to settings
    if request:
        base = f"{request.scheme}://{request.get_host()}"
    else:
        base = getattr(settings, "MEDIA_BASE_URL", settings.MEDIA_URL)
    
    normalized = (file_url or "").lstrip("/")
    normalized = normalized.replace("business/images/business/images/", "business/images/")
    return f"{base.rstrip('/')}/{normalized}"


def _serialize_business_item(b, request=None):
    publish_dt = b.published_at or b.updated_at or b.created_at
    created_by_name = None
    if b.created_by:
        if hasattr(b.created_by, "get_full_name"):
            created_by_name = b.created_by.get_full_name() or None
        if not created_by_name:
            created_by_name = getattr(b.created_by, "username", None) or str(b.created_by)

    return {
        "id": b.id,
        "name": b.name,
        "slug": b.slug,
        "category_id": b.category_id,
        "category": b.category.name if b.category else "Uncategorized",
        "category_icon": b.category.icon if b.category else "",
        "service": b.service,
        "location": b.location,
        "phone": b.phone,
        "details": b.details,
        "address": b.address,
        "area": b.area,
        "working_hours": b.working_hours,
        "price_range_min": b.price_range_min,
        "price_range_max": b.price_range_max,
        "price_range": b.price_range,
        "status": b.status,
        "status_code": STATUS_CODE_MAP.get(b.status),
        "created_by_id": b.created_by_id,
        "created_by_name": created_by_name,
        "created_at": timezone.localtime(b.created_at).isoformat() if b.created_at else None,
        "updated_at": timezone.localtime(b.updated_at).isoformat() if b.updated_at else None,
        "published_at": timezone.localtime(publish_dt).isoformat() if publish_dt else None,
        "image_url": _public_media_url(b.image.url, request) if b.image else None,
    }


def _single_record_navigation(request, business_qs, current_obj):
    ordered_ids = list(business_qs.values_list("id", flat=True))
    try:
        idx = ordered_ids.index(current_obj.id)
    except ValueError:
        return {
            "previous": None,
            "next": None,
            "previous_item": None,
            "next_item": None,
        }

    prev_obj = None
    next_obj = None

    if idx > 0:
        prev_obj = business_qs.filter(id=ordered_ids[idx - 1]).first()
    if idx < len(ordered_ids) - 1:
        next_obj = business_qs.filter(id=ordered_ids[idx + 1]).first()

    return {
        "previous": request.build_absolute_uri(f"{request.path}?id={prev_obj.id}") if prev_obj else None,
        "next": request.build_absolute_uri(f"{request.path}?id={next_obj.id}") if next_obj else None,
        "previous_item": _serialize_business_item(prev_obj) if prev_obj else None,
        "next_item": _serialize_business_item(next_obj) if next_obj else None,
    }


# =====================================================
# 🔐 HELPER: GET LOGGED-IN MEMBER
# =====================================================
def get_logged_in_member(request):
    member_no = request.session.get('member_no')
    if not member_no:
        return None
    try:
        return Member.objects.get(member_no=member_no)
    except Member.DoesNotExist:
        return None


# =====================================================
# 📋 BUSINESS LIST (SESSION BASED)
# =====================================================
def business_list(request):
    member = get_logged_in_member(request)
    if not member:
        return redirect('member:customer_login')

    published_business = Business.objects.filter(
        status="published",
        created_by=member
    )
    unpublished_business = Business.objects.exclude(
        status="published"
    ).filter(created_by=member)

    return render(request, "html_member/html_business/business_list.html", {
        "published_business": published_business,
        "unpublished_business": unpublished_business,
    })


# =====================================================
# ➕✏️ ADD + EDIT BUSINESS (SESSION BASED)
# =====================================================
def business_form(request, pk=None):
    member = get_logged_in_member(request)
    if not member:
        return redirect('member:customer_login')

    business = get_object_or_404(Business, pk=pk) if pk else None

    # 🔐 ownership check
    if business and business.created_by != member:
        return redirect("business:business_list")

    if request.method == "POST":
        name = request.POST.get("name")
        service = request.POST.get("service")
        location = request.POST.get("location")
        phone = request.POST.get("phone")
        details = request.POST.get("details")
        category_id = request.POST.get("category")
        action = (request.POST.get("action") or "").strip().lower()
        image = request.FILES.get("image")
        address = request.POST.get("address")
        area = request.POST.get("area")
        working_hours = request.POST.get("working_hours")
        price_range_min = request.POST.get("price_range_min")
        price_range_max = request.POST.get("price_range_max")

        if business:
            # UPDATE
            previous_status = business.status
            if action == "save_draft":
                status = "draft"
            elif action == "submit_review":
                status = "inreview"
            else:
                status = "inreview" if previous_status in {"published", "rejected", "inreview"} else "draft"

            if previous_status in {"published", "rejected"}:
                # Any member edits on published/rejected content must be reviewed again.
                status = "inreview"

            business.name = name
            business.service = service
            business.location = location
            business.phone = phone
            business.details = details
            business.category_id = category_id or None
            business.status = status
            business.updated_by = member
            business.address = address
            business.area = area
            business.working_hours = working_hours
            
            if price_range_min:
                business.price_range_min = int(price_range_min)
            else:
                business.price_range_min = None
                
            if price_range_max:
                business.price_range_max = int(price_range_max)
            else:
                business.price_range_max = None

            if image:
                if business.image:
                    business.image.delete(save=False)
                business.image.save(_business_image_name(business.pk, image.name), image, save=False)

            if status == "published" and (previous_status != "published" or not business.published_at):
                business.published_at = timezone.now()
            elif status != "published":
                business.published_at = None

            business.save()

        else:
            # CREATE
            status = "inreview" if action == "submit_review" else "draft"
            
            price_min = None
            price_max = None
            if price_range_min:
                try:
                    price_min = int(price_range_min)
                except ValueError:
                    pass
            if price_range_max:
                try:
                    price_max = int(price_range_max)
                except ValueError:
                    pass
            
            created_business = Business.objects.create(
                name=name,
                service=service,
                location=location,
                phone=phone,
                details=details,
                category_id=category_id or None,
                status=status,
                image=None,
                created_by=member,
                updated_by=member,
                published_at=timezone.now() if status == "published" else None,
                address=address,
                area=area,
                working_hours=working_hours,
                price_range_min=price_min,
                price_range_max=price_max,
            )
            if image:
                created_business.image.save(
                    _business_image_name(created_business.pk, image.name),
                    image,
                    save=True,
                )

        return redirect("business:business_list")

    categories = BusinessCategory.objects.filter(is_active=True)

    return render(request, "html_member/html_business/business_form.html", {
        "business": business,
        "categories": categories,
        "status_choices": Business.STATUS_CHOICES,
    })


# =====================================================
# 🗑 DELETE BUSINESS (SESSION BASED)
# =====================================================
def business_delete(request, pk):
    member = get_logged_in_member(request)
    if not member:
        return redirect('member:login')

    business = get_object_or_404(Business, pk=pk)

    if business.created_by != member:
        return redirect("business:business_list")

    business.delete()
    return redirect("business:business_list")


# =====================================================
# 🌐 PUBLIC JSON APIs
# =====================================================
def api_category_list(request):
    categories = BusinessCategory.objects.filter(is_active=True).order_by("name")
    data = [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "icon": c.icon,
            "count": c.businesses.filter(status="published").count(),
        }
        for c in categories
    ]

    # Include virtual category for posts where category is null.
    uncategorized_count = Business.objects.filter(
        status="published",
        category__isnull=True,
    ).count()
    data.append(
        {
            "id": 0,
            "name": "Uncategorized",
            "slug": "uncategorized",
            "icon": "",
            "count": uncategorized_count,
        }
    )
    return JsonResponse({"count": len(data), "results": data})


def api_all_business(request):
    ordering_mode = "-published_at"

    business_qs = (
        Business.objects
        .select_related("category", "created_by")
        .filter(status="published")
        .order_by("-published_at")
    )

    requested_id = (request.GET.get("id") or request.GET.get("business_id") or "").strip()
    requested_slug = (request.GET.get("slug") or request.GET.get("business_slug") or "").strip()

    if requested_id:
        try:
            requested_id = int(requested_id)
        except ValueError:
            return JsonResponse({"detail": "Invalid id value"}, status=400)

        business_item = business_qs.filter(id=requested_id).first()
        if not business_item:
            return JsonResponse({"detail": "Business not found", "id": requested_id}, status=404)
        nav_qs = (
            Business.objects
            .select_related("category", "created_by")
            .filter(status="published")
            .order_by("-published_at")
        )
        nav = _single_record_navigation(request, nav_qs, business_item)
        return JsonResponse(
            {
                "result": _serialize_business_item(business_item),
                "ordering": ordering_mode,
                "previous": nav["previous"],
                "next": nav["next"],
                "previous_item": nav["previous_item"],
                "next_item": nav["next_item"],
            }
        )

    if requested_slug:
        business_item = business_qs.filter(slug=requested_slug).first()
        if not business_item:
            return JsonResponse({"detail": "Business not found", "slug": requested_slug}, status=404)
        nav_qs = (
            Business.objects
            .select_related("category", "created_by")
            .filter(status="published")
            .order_by("-published_at")
        )
        nav = _single_record_navigation(request, nav_qs, business_item)
        return JsonResponse(
            {
                "result": _serialize_business_item(business_item),
                "ordering": ordering_mode,
                "previous": nav["previous"],
                "next": nav["next"],
                "previous_item": nav["previous_item"],
                "next_item": nav["next_item"],
            }
        )

    # Filter by category
    category_id = request.GET.get("category_id")
    category_slug = request.GET.get("category_slug")
    category_name = request.GET.get("category")
    
    if category_id:
        if not category_id.lower() in {"none", "null"}:
            business_qs = business_qs.filter(category_id=category_id)
        else:
            business_qs = business_qs.filter(category__isnull=True)
    elif category_slug:
        if not category_slug.lower() in {"uncategorized", "uncategories", "no-category", "none", "null"}:
            business_qs = business_qs.filter(category__slug=category_slug)
        else:
            business_qs = business_qs.filter(category__isnull=True)
    elif category_name:
        compact_name = " ".join(category_name.split())
        if not compact_name.lower() in {"uncategorized", "uncategories", "no category", "none", "null"}:
            business_qs = business_qs.filter(
                Q(category__name__iexact=compact_name) |
                Q(category__name__istartswith=compact_name)
            )

    # Filter by location
    location = request.GET.get("location")
    if location:
        business_qs = business_qs.filter(location__icontains=location)

    # Search
    search = request.GET.get("search") or request.GET.get("q") or ""
    if search:
        business_qs = business_qs.filter(
            Q(name__icontains=search) |
            Q(service__icontains=search) |
            Q(location__icontains=search) |
            Q(details__icontains=search) |
            Q(area__icontains=search)
        )

    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size") or request.GET.get("per_page") or 10
    try:
        page_size = max(1, int(page_size))
    except (TypeError, ValueError):
        page_size = 10

    paginator = Paginator(business_qs, page_size)
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages) if paginator.num_pages else []
    except Exception:
        page_obj = paginator.page(1) if paginator.num_pages else []

    results = []
    iterable = page_obj.object_list if paginator.num_pages else []
    current_for_index = page_obj.number if paginator.num_pages else 1
    start_index = ((current_for_index - 1) * page_size) if paginator.num_pages else 0
    for idx, b in enumerate(iterable, start=1):
        item = _serialize_business_item(b, request)
        item["line_no"] = start_index + idx
        results.append(item)

    if paginator.num_pages:
        current_page = page_obj.number
        total_pages = paginator.num_pages
        has_next = page_obj.has_next()
        has_previous = page_obj.has_previous()
    else:
        current_page = 1
        total_pages = 0
        has_next = False
        has_previous = False

    next_url = None
    prev_url = None
    if has_next:
        next_params = request.GET.copy()
        next_params["page"] = current_page + 1
        next_url = request.build_absolute_uri(f"{request.path}?{next_params.urlencode()}")
    if has_previous:
        prev_params = request.GET.copy()
        prev_params["page"] = current_page - 1
        prev_url = request.build_absolute_uri(f"{request.path}?{prev_params.urlencode()}")

    return JsonResponse(
        {
            "count": paginator.count,
            "page": current_page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_previous": has_previous,
            "ordering": ordering_mode,
            "next_page": (current_page + 1) if has_next else None,
            "previous_page": (current_page - 1) if has_previous else None,
            "next": next_url,
            "previous": prev_url,
            "category_filter": {
                "category_id": category_id,
                "category_slug": category_slug,
                "category": category_name,
            },
            "location_filter": location,
            "search_filter": search,
            "results": results,
        }
    )


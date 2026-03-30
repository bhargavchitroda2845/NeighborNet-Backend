from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
import os

from .models import News,Category
from member.models import Member

STATUS_CODE_MAP = {
    "inreview": 0,
    "published": 1,
    "rejected": 2,
    "draft": 3,
}


def _news_image_name(news_pk, original_name):
    ext = os.path.splitext(original_name or "")[1].lower() or ".jpg"
    # `upload_to="news/images/"` is already defined on the model,
    # so only return a filename to avoid duplicated path segments.
    return f"image{news_pk}{ext}"


def _public_media_url(file_url):
    base = getattr(settings, "MEDIA_BASE_URL", settings.MEDIA_URL)
    normalized = (file_url or "").lstrip("/")
    # Backward compatibility for old records saved with duplicated path.
    normalized = normalized.replace("news/images/news/images/", "news/images/")
    return f"{base.rstrip('/')}/{normalized}"


def _serialize_news_item(n):
    publish_dt = n.published_at or n.updated_at or n.created_at
    created_by_name = None
    if n.created_by:
        if hasattr(n.created_by, "get_full_name"):
            created_by_name = n.created_by.get_full_name() or None
        if not created_by_name:
            created_by_name = getattr(n.created_by, "username", None) or str(n.created_by)

    return {
        "id": n.id,
        "title": n.title,
        "slug": n.slug,
        "content": n.content,
        "category_id": n.category_id,
        "category": n.category.name if n.category else "Uncategorized",
        "category_slug": n.category.slug if n.category else "uncategorized",
        "status": n.status,
        "status_code": STATUS_CODE_MAP.get(n.status),
        "created_by_id": n.created_by_id,
        "created_by_name": created_by_name,
        "created_at": timezone.localtime(n.created_at).isoformat() if n.created_at else None,
        "updated_at": timezone.localtime(n.updated_at).isoformat() if n.updated_at else None,
        "published_at": timezone.localtime(publish_dt).isoformat() if publish_dt else None,
        "image_url": _public_media_url(n.image.url) if n.image else None,
    }


def _single_record_navigation(request, news_qs, current_obj):
    ordered_ids = list(news_qs.values_list("id", flat=True))
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
        prev_obj = news_qs.filter(id=ordered_ids[idx - 1]).first()
    if idx < len(ordered_ids) - 1:
        next_obj = news_qs.filter(id=ordered_ids[idx + 1]).first()

    return {
        "previous": request.build_absolute_uri(f"{request.path}?id={prev_obj.id}") if prev_obj else None,
        "next": request.build_absolute_uri(f"{request.path}?id={next_obj.id}") if next_obj else None,
        "previous_item": _serialize_news_item(prev_obj) if prev_obj else None,
        "next_item": _serialize_news_item(next_obj) if next_obj else None,
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
# 📰 NEWS LIST (SESSION BASED)
# =====================================================
def news_list(request):
    member = get_logged_in_member(request)
    if not member:
        return redirect('member:customer_login')

    published_news = News.objects.filter(
        status="published",
        created_by=member
    )
    unpublished_news = News.objects.exclude(
        status="published"
    ).filter(created_by=member)

    return render(request, "html_member/news_list.html", {
        "published_news": published_news,
        "unpublished_news": unpublished_news,
    })


# =====================================================
# ➕✏️ ADD + EDIT NEWS (SESSION BASED)
# =====================================================
def news_form(request, pk=None):
    member = get_logged_in_member(request)
    if not member:
        return redirect('member:customer_login')

    news = get_object_or_404(News, pk=pk) if pk else None

    # 🔐 ownership check
    if news and news.created_by != member:
        return redirect("news:news_list")

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        category_id = request.POST.get("category")
        action = (request.POST.get("action") or "").strip().lower()
        image = request.FILES.get("image")

        if news:
            # UPDATE
            previous_status = news.status
            if action == "save_draft":
                status = "draft"
            elif action == "submit_review":
                status = "inreview"
            else:
                status = "inreview" if previous_status in {"published", "rejected", "inreview"} else "draft"

            if previous_status in {"published", "rejected"}:
                # Any member edits on published/rejected content must be reviewed again.
                status = "inreview"

            news.title = title
            news.content = content
            # Allow clearing category if blank
            news.category_id = category_id or None
            news.status = status
            news.updated_by = member

            if image:
                if news.image:
                    news.image.delete(save=False)
                news.image.save(_news_image_name(news.pk, image.name), image, save=False)

            if status == "published" and (previous_status != "published" or not news.published_at):
                # Set publish time at the moment it becomes published.
                news.published_at = timezone.now()
            elif status != "published":
                news.published_at = None

            news.save()

        else:
            # CREATE
            status = "inreview" if action == "submit_review" else "draft"
            created_news = News.objects.create(
                title=title,
                content=content,
                category_id=category_id or None,
                status=status,
                image=None,
                created_by=member,
                updated_by=member,
                published_at=timezone.now() if status == "published" else None,
            )
            if image:
                created_news.image.save(
                    _news_image_name(created_news.pk, image.name),
                    image,
                    save=True,
                )

        return redirect("news:news_list")

    categories = Category.objects.filter(is_active=True)

    return render(request, "html_member/news_form.html", {
        "news": news,
        "categories": categories,
        "status_choices": News.STATUS_CHOICES,
    })


# =====================================================
# 🗑 DELETE NEWS (SESSION BASED)
# =====================================================
def news_delete(request, pk):
    member = get_logged_in_member(request)
    if not member:
        return redirect('member:login')

    news = get_object_or_404(News, pk=pk)

    if news.created_by != member:
        return redirect("news:news_list")

    news.delete()
    return redirect("news:news_list")


# =====================================================
# 🌐 PUBLIC JSON APIs
# =====================================================
def api_category_list(request):
    categories = Category.objects.filter(is_active=True).order_by("name")
    data = [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "count": c.news_items.filter(status="published").count(),
        }
        for c in categories
    ]

    # Include virtual category for posts where category is null.
    uncategorized_count = News.objects.filter(
        status="published",
        category__isnull=True,
    ).count()
    data.append(
        {
            "id": 0,
            "name": "Uncategorized",
            "slug": "uncategorized",
            "count": uncategorized_count,
        }
    )
    return JsonResponse({"count": len(data), "results": data})


def api_all_news(request):
    ordering_mode = "-published_at"

    news_qs = (
        News.objects
        .select_related("category", "created_by")
        .filter(status="published")
        .order_by("-published_at")
    )

    requested_id = (request.GET.get("id") or request.GET.get("news_id") or request.GET.get("post_id") or "").strip()
    requested_slug = (request.GET.get("slug") or request.GET.get("news_slug") or request.GET.get("post_slug") or "").strip()

    if requested_id:
        try:
            requested_id = int(requested_id)
        except ValueError:
            return JsonResponse({"detail": "Invalid id value"}, status=400)

        news_item = news_qs.filter(id=requested_id).first()
        if not news_item:
            return JsonResponse({"detail": "News not found", "id": requested_id}, status=404)
        nav_qs = (
            News.objects
            .select_related("category", "created_by")
            .filter(status="published")
            .order_by("-published_at")
        )
        nav = _single_record_navigation(request, nav_qs, news_item)
        return JsonResponse(
            {
                "result": _serialize_news_item(news_item),
                "ordering": ordering_mode,
                "previous": nav["previous"],
                "next": nav["next"],
                "previous_item": nav["previous_item"],
                "next_item": nav["next_item"],
            }
        )

    if requested_slug:
        news_item = news_qs.filter(slug=requested_slug).first()
        if not news_item:
            return JsonResponse({"detail": "News not found", "slug": requested_slug}, status=404)
        nav_qs = (
            News.objects
            .select_related("category", "created_by")
            .filter(status="published")
            .order_by("-published_at")
        )
        nav = _single_record_navigation(request, nav_qs, news_item)
        return JsonResponse(
            {
                "result": _serialize_news_item(news_item),
                "ordering": ordering_mode,
                "previous": nav["previous"],
                "next": nav["next"],
                "previous_item": nav["previous_item"],
                "next_item": nav["next_item"],
            }
        )

    has_category_id_param = "category_id" in request.GET
    has_category_slug_param = "category_slug" in request.GET
    has_category_param = "category" in request.GET
    category_id = (
        request.GET.get("category_id")
        or request.GET.get("catgory_id")
        or request.GET.get("cat_id")
        or ""
    ).strip()
    category_slug = (
        request.GET.get("category_slug")
        or request.GET.get("categories_slug")
        or ""
    ).strip()
    category_name = (
        request.GET.get("category")
        or request.GET.get("category_name")
        or request.GET.get("categories_name")
        or request.GET.get("cat_name")
        or ""
    ).strip()

    if category_id and not has_category_id_param:
        has_category_id_param = True
    if category_slug and not has_category_slug_param:
        has_category_slug_param = True
    if category_name and not has_category_param:
        has_category_param = True

    if has_category_id_param:
        if not category_id or category_id.lower() in {"none", "null"}:
            news_qs = news_qs.filter(category__isnull=True)
        else:
            news_qs = news_qs.filter(category_id=category_id)
    elif has_category_slug_param:
        if not category_slug or category_slug.lower() in {"uncategorized", "uncategories", "no-category", "none", "null"}:
            news_qs = news_qs.filter(category__isnull=True)
        else:
            news_qs = news_qs.filter(category__slug=category_slug)
    elif has_category_param:
        # Be tolerant of user-entered spacing/casing issues in category query values.
        compact_name = " ".join(category_name.split())
        if not compact_name or compact_name.lower() in {"uncategorized", "uncategories", "no category", "none", "null"}:
            news_qs = news_qs.filter(category__isnull=True)
        else:
            news_qs = news_qs.filter(
                Q(category__name__iexact=compact_name) |
                Q(category__name__istartswith=compact_name)
            )

    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size") or request.GET.get("per_page") or 10
    try:
        page_size = max(1, int(page_size))
    except (TypeError, ValueError):
        page_size = 10

    paginator = Paginator(news_qs, page_size)
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
    for idx, n in enumerate(iterable, start=1):
        item = _serialize_news_item(n)
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
            "news_filter": {
                "id": requested_id if requested_id else None,
                "slug": requested_slug or None,
            },
            "results": results,
        }
    )

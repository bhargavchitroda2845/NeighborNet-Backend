from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from member.models import Member
from .forms import BnsModelForm
from .models import BnsModel, Bid

STATUS_CODE_MAP = {
    BnsModel.STATUS_INREVIEW: 0,
    BnsModel.STATUS_PUBLISHED: 1,
    BnsModel.STATUS_REJECTED: 2,
    BnsModel.STATUS_DRAFT: 3,
}


def _serialize_member_profile(member_obj, fallback_username=None):
    if not member_obj and not fallback_username:
        return None

    if not member_obj:
        return {
            "member_no": None,
            "username": fallback_username,
            "first_name": None,
            "surname": None,
            "full_name": fallback_username,
        }

    full_name = f"{member_obj.first_name} {member_obj.surname}".strip()
    return {
        "member_no": member_obj.member_no,
        "username": member_obj.username,
        "first_name": member_obj.first_name,
        "surname": member_obj.surname,
        "full_name": full_name or member_obj.username,
    }


def _public_media_url(file_url):
    base = getattr(settings, "MEDIA_BASE_URL", "http://192.168.1.4/media")
    normalized = (file_url or "").lstrip("/")
    return f"{base.rstrip('/')}/{normalized}"


def _published_ordered_queryset(base_qs=None):
    qs = base_qs if base_qs is not None else BnsModel.objects.all()
    return qs.order_by(F("published_at").desc(nulls_last=True), "-id")


def get_logged_in_member(request):
    member_no = request.session.get("member_no")
    if not member_no:
        return None
    try:
        return Member.objects.get(member_no=member_no)
    except Member.DoesNotExist:
        return None


def member_marketplace_list(request):
    member = get_logged_in_member(request)
    if not member:
        return redirect("/member/login/")

    items = BnsModel.objects.filter(created_by=member).order_by("-created_at")
    
    # Add bid counts for each item
    for item in items:
        item.bid_count = item.bids.count()
        item.pending_bid_count = item.bids.filter(status=Bid.STATUS_PENDING).count()
    
    return render(
        request,
        "html_member/html_marketplace/marketplace_list.html",
        {"items": items},
    )


def member_marketplace_form(request, pk=None):
    member = get_logged_in_member(request)
    if not member:
        return redirect("/member/login/")

    item = get_object_or_404(BnsModel, pk=pk, created_by=member) if pk else None

    if request.method == "POST":
        form = BnsModelForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            obj = form.save(commit=False)
            action = (request.POST.get("action") or "").strip().lower()
            previous_status = item.status if item else None

            if action == "save_draft":
                status = BnsModel.STATUS_DRAFT
            elif action == "submit_review":
                status = BnsModel.STATUS_INREVIEW
            else:
                status = previous_status or BnsModel.STATUS_DRAFT

            if previous_status in {BnsModel.STATUS_PUBLISHED, BnsModel.STATUS_REJECTED}:
                status = BnsModel.STATUS_INREVIEW

            obj.status = status
            if not obj.pk:
                obj.created_by = member
                obj.created_by_username = member.username
            obj.updated_by = member
            obj.updated_by_username = member.username
            obj.save()
            return redirect("marketplace:member_marketplace_list")
    else:
        form = BnsModelForm(instance=item)

    return render(
        request,
        "html_member/html_marketplace/marketplace_form.html",
        {"form": form, "item": item},
    )


def member_marketplace_delete(request, pk):
    member = get_logged_in_member(request)
    if not member:
        return redirect("/member/login/")

    item = get_object_or_404(BnsModel, pk=pk, created_by=member)
    if request.method == "POST":
        item.delete()
        return redirect("marketplace:member_marketplace_list")
    return render(
        request,
        "html_member/html_marketplace/marketplace_delete_confirm.html",
        {"item": item},
    )


def member_marketplace_bids(request, pk):
    """View to see all bids for a specific marketplace item"""
    member = get_logged_in_member(request)
    if not member:
        return redirect("/member/login/")

    item = get_object_or_404(BnsModel, pk=pk, created_by=member)
    bids = item.bids.all().order_by("-created_at")
    
    # Force evaluation of querysets to get accurate counts and convert to lists
    pending_bids = list(bids.filter(status=Bid.STATUS_PENDING))
    accepted_bids = list(bids.filter(status=Bid.STATUS_ACCEPTED))
    rejected_bids = list(bids.filter(status=Bid.STATUS_REJECTED))
    
    # Store counts as separate variables for the template
    pending_count = len(pending_bids)
    accepted_count = len(accepted_bids)
    rejected_count = len(rejected_bids)
    
    return render(
        request,
        "html_member/html_marketplace/marketplace_bids.html",
        {
            "item": item,
            "bids": bids,
            "pending_bids": pending_bids,
            "accepted_bids": accepted_bids,
            "rejected_bids": rejected_bids,
            "pending_count": pending_count,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
        },
    )


def send_winner_email(bid):
    """Send email notification to the winner of a bid"""
    from django.core.mail import send_mail
    
    bidder = bid.bidder
    item = bid.marketplace_item
    
    # Get bidder's email
    bidder_email = None
    if hasattr(bidder, 'email_id') and bidder.email_id:
        bidder_email = bidder.email_id
    elif hasattr(bidder, 'email') and bidder.email:
        bidder_email = bidder.email
    
    if not bidder_email:
        # Try to get from member detail
        try:
            from member.models import MemberDetail
            member_detail = MemberDetail.objects.filter(member=bidder).first()
            if member_detail and member_detail.email_id:
                bidder_email = member_detail.email_id
        except:
            pass
    
    if not bidder_email:
        print(f"Could not find email for bidder {bidder.username}")
        return False
    
    subject = f"Congratulations! You won the bid for '{item.title}'"
    
    message = f"""
Dear {bidder.first_name or bidder.username},

Congratulations! Your bid has been accepted and you are the winner!

Listing Details:
- Title: {item.title}
- Your Bid Amount: Rs {bid.bid_amount}
- Message: {bid.message or 'N/A'}

Please contact the seller for further details:
- Contact: {item.contact}
- Area: {item.area or 'N/A'}

Thank you for using NeighborNet!

Best regards,
NeighborNet Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [bidder_email],
            fail_silently=False,
        )
        print(f"Winner email sent to {bidder_email} for bid {bid.id}")
        return True
    except Exception as e:
        print(f"Error sending winner email: {e}")
        return False


def member_marketplace_bid_action(request, pk, action):
    """Handle accept/reject/win actions for bids"""
    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    try:
        bid = Bid.objects.get(pk=pk)
    except Bid.DoesNotExist:
        return JsonResponse({"detail": "Bid not found"}, status=404)

    if bid.marketplace_item.created_by != member:
        return JsonResponse({"detail": "You can only manage bids on your own items"}, status=403)

    if action == "accept":
        # Accept bid - move to accepted section (but NOT winner yet)
        bid.status = Bid.STATUS_ACCEPTED
        bid.is_winner = False  # Not winner yet - user needs to click "Win Bid" separately
        bid.save()
        
        return JsonResponse({
            "success": True, 
            "message": "Bid accepted! The bid is now in the Accepted Bids section. You can mark it as Winner when ready.", 
            "status": bid.status,
            "is_winner": bid.is_winner
        })
    elif action == "win":
        # Mark as winner and send email notification
        # First, unmark any previous winners for this item
        Bid.objects.filter(
            marketplace_item=bid.marketplace_item,
            is_winner=True
        ).update(is_winner=False)
        
        bid.is_winner = True
        bid.save()
        
        # Send winner email notification with seller contact details
        email_sent = send_winner_email(bid)
        
        if email_sent:
            return JsonResponse({
                "success": True, 
                "message": "Bid marked as Winner! The bidder has been notified via email with your contact details.", 
                "status": bid.status,
                "is_winner": bid.is_winner,
                "winner_notified": True
            })
        else:
            return JsonResponse({
                "success": True, 
                "message": "Bid marked as Winner! (Could not send email notification)", 
                "status": bid.status,
                "is_winner": bid.is_winner,
                "winner_notified": False
            })
    elif action == "reject":
        bid.status = Bid.STATUS_REJECTED
        bid.is_winner = False
        bid.save()
        return JsonResponse({"success": True, "message": "Bid rejected", "status": bid.status})
    elif action == "mark_sold":
        # Mark the bid as winner AND mark the item as sold
        # First, unmark any previous winners for this item
        Bid.objects.filter(
            marketplace_item=bid.marketplace_item,
            is_winner=True
        ).update(is_winner=False)
        
        bid.is_winner = True
        bid.status = Bid.STATUS_ACCEPTED
        bid.save()
        
        # Mark the marketplace item as sold
        marketplace_item = bid.marketplace_item
        marketplace_item.status = "sold"  # Custom status for sold items
        marketplace_item.save()
        
        # Send winner email notification
        email_sent = send_winner_email(bid)
        
        if email_sent:
            return JsonResponse({
                "success": True, 
                "message": "Item marked as SOLD! The bidder has been notified via email.", 
                "status": bid.status,
                "is_winner": bid.is_winner,
                "item_sold": True,
                "winner_notified": True
            })
        else:
            return JsonResponse({
                "success": True, 
                "message": "Item marked as SOLD! (Could not send email notification)", 
                "status": bid.status,
                "is_winner": bid.is_winner,
                "item_sold": True,
                "winner_notified": False
            })
    else:
        return JsonResponse({"detail": "Invalid action. Use 'accept', 'reject', 'win', or 'mark_sold'"}, status=400)


def _serialize_bns_item(item):
    created_profile = _serialize_member_profile(item.created_by, item.created_by_username)
    updated_profile = _serialize_member_profile(item.updated_by, item.updated_by_username)
    return {
        "id": item.id,
        "title": item.title,
        "slug": item.slug,
        "desc": item.desc,
        "listing_type": item.listing_type,
        "listing_type_label": item.get_listing_type_display(),
        "status": item.status,
        "status_code": STATUS_CODE_MAP.get(item.status),
        "status_label": item.get_status_display(),
        "area": item.area,
        "contact": item.contact,
        "min_price": item.min_price,
        "max_price": item.max_price,
        "price": item.price,
        "image_url": _public_media_url(item.image.url) if item.image else None,
        "created_by": created_profile["full_name"] if created_profile else None,
        "updated_by": updated_profile["full_name"] if updated_profile else None,
        "created_by_profile": created_profile,
        "updated_by_profile": updated_profile,
        "created_at": timezone.localtime(item.created_at).isoformat() if item.created_at else None,
        "published_at": timezone.localtime(item.published_at).isoformat() if item.published_at else None,
        "updated_at": timezone.localtime(item.updated_at).isoformat() if item.updated_at else None,
        "bidding_enabled": item.bidding_enabled,
    }


def _single_record_navigation(request, qs, current_obj):
    ordered_ids = list(qs.values_list("id", flat=True))
    try:
        idx = ordered_ids.index(current_obj.id)
    except ValueError:
        return {"previous": None, "next": None, "previous_item": None, "next_item": None}

    prev_obj = qs.filter(id=ordered_ids[idx - 1]).first() if idx > 0 else None
    next_obj = qs.filter(id=ordered_ids[idx + 1]).first() if idx < len(ordered_ids) - 1 else None
    return {
        "previous": request.build_absolute_uri(f"{request.path}?id={prev_obj.id}") if prev_obj else None,
        "next": request.build_absolute_uri(f"{request.path}?id={next_obj.id}") if next_obj else None,
        "previous_item": _serialize_bns_item(prev_obj) if prev_obj else None,
        "next_item": _serialize_bns_item(next_obj) if next_obj else None,
    }


def api_listing_type_list(request):
    data = []
    for key, label in BnsModel.LISTING_TYPE_CHOICES:
        data.append(
            {
                "key": key,
                "label": label,
                "count": BnsModel.objects.filter(
                    listing_type=key,
                    status=BnsModel.STATUS_PUBLISHED,
                ).count(),
            }
        )
    return JsonResponse({"count": len(data), "results": data})


def api_all_marketplace(request):
    ordering_mode = "-published_at"
    status_filter = BnsModel.STATUS_PUBLISHED
    base_qs = BnsModel.objects.select_related("created_by", "updated_by")
    base_qs = base_qs.filter(status=status_filter)

    qs = _published_ordered_queryset(base_qs)

    requested_id = (request.GET.get("id") or request.GET.get("item_id") or "").strip()
    requested_slug = (request.GET.get("slug") or request.GET.get("item_slug") or "").strip()

    if requested_id:
        try:
            requested_id = int(requested_id)
        except ValueError:
            return JsonResponse({"detail": "Invalid id value"}, status=400)

        item = qs.filter(id=requested_id).first()
        if not item:
            return JsonResponse({"detail": "Item not found", "id": requested_id}, status=404)

        nav = _single_record_navigation(request, qs, item)
        return JsonResponse(
            {
                "result": _serialize_bns_item(item),
                "ordering": ordering_mode,
                "previous": nav["previous"],
                "next": nav["next"],
                "previous_item": nav["previous_item"],
                "next_item": nav["next_item"],
            }
        )

    if requested_slug:
        item = qs.filter(slug=requested_slug).first()
        if not item:
            return JsonResponse({"detail": "Item not found", "slug": requested_slug}, status=404)

        nav = _single_record_navigation(request, qs, item)
        return JsonResponse(
            {
                "result": _serialize_bns_item(item),
                "ordering": ordering_mode,
                "previous": nav["previous"],
                "next": nav["next"],
                "previous_item": nav["previous_item"],
                "next_item": nav["next_item"],
            }
        )

    listing_type = (
        request.GET.get("listing_type")
        or request.GET.get("type")
        or request.GET.get("category")
        or ""
    ).strip().lower()
    area = (request.GET.get("area") or "").strip()
    search = (request.GET.get("search") or request.GET.get("q") or "").strip()

    if listing_type:
        qs = qs.filter(listing_type=listing_type)
    if area:
        qs = qs.filter(area__icontains=area)
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(desc__icontains=search)
            | Q(area__icontains=area)
            | Q(contact__icontains=search)
        )

    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size") or request.GET.get("per_page") or 10
    try:
        page_size = max(1, int(page_size))
    except (TypeError, ValueError):
        page_size = 10

    paginator = Paginator(qs, page_size)
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
    for idx, item in enumerate(iterable, start=1):
        record = _serialize_bns_item(item)
        record["line_no"] = start_index + idx
        results.append(record)

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
            "filters": {
                "status": status_filter,
                "listing_type": listing_type or None,
                "area": area or None,
                "search": search or None,
            },
            "item_filter": {
                "id": requested_id if requested_id else None,
                "slug": requested_slug or None,
            },
            "results": results,
        }
    )


# Bid API endpoints - with CSRF exemption for cross-origin requests
@csrf_exempt
def api_place_bid(request):
    """API to place a bid on a marketplace item"""
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    item_id = request.POST.get("item_id")
    bid_amount = request.POST.get("bid_amount")
    message = request.POST.get("message", "")

    if not item_id or not bid_amount:
        return JsonResponse({"detail": "item_id and bid_amount are required"}, status=400)

    try:
        item_id = int(item_id)
        bid_amount = int(bid_amount)
    except ValueError:
        return JsonResponse({"detail": "Invalid item_id or bid_amount"}, status=400)

    try:
        item = BnsModel.objects.get(id=item_id, status=BnsModel.STATUS_PUBLISHED)
    except BnsModel.DoesNotExist:
        return JsonResponse({"detail": "Item not found"}, status=404)

    if not item.bidding_enabled:
        return JsonResponse({"detail": "Bidding is not enabled for this item"}, status=400)

    if item.created_by == member:
        return JsonResponse({"detail": "You cannot bid on your own item"}, status=400)

    # Check if user already bid on this item
    existing_bid = Bid.objects.filter(marketplace_item=item, bidder=member).first()
    if existing_bid:
        # Allow re-bidding if the previous bid was rejected
        if existing_bid.status == Bid.STATUS_REJECTED:
            # Delete the old rejected bid and allow new bid
            existing_bid.delete()
        elif existing_bid.status == Bid.STATUS_PENDING:
            return JsonResponse({"detail": "You have already placed a bid on this item. It is pending review."}, status=400)
        elif existing_bid.status == Bid.STATUS_ACCEPTED:
            return JsonResponse({"detail": "You already have an accepted bid on this item"}, status=400)
        else:
            return JsonResponse({"detail": "You have already placed a bid on this item"}, status=400)

    if item.min_price and bid_amount < item.min_price:
        return JsonResponse({"detail": f"Bid amount must be at least {item.min_price}"}, status=400)

    bid = Bid.objects.create(
        marketplace_item=item,
        bidder=member,
        bid_amount=bid_amount,
        message=message
    )

    return JsonResponse({
        "success": True,
        "message": "Bid placed successfully",
        "bid_id": bid.id
    })


@csrf_exempt
def api_get_bids(request, item_id):
    """API to get bids for a marketplace item"""
    try:
        item_id = int(item_id)
    except ValueError:
        return JsonResponse({"detail": "Invalid item_id"}, status=400)

    try:
        item = BnsModel.objects.get(id=item_id)
    except BnsModel.DoesNotExist:
        return JsonResponse({"detail": "Item not found"}, status=404)

    member = get_logged_in_member(request)
    is_owner = member and item.created_by == member

    bids = item.bids.all()

    if not is_owner:
        bids = bids.filter(status=Bid.STATUS_ACCEPTED)

    results = []
    for bid in bids:
        bid_data = {
            "id": bid.id,
            "bid_amount": bid.bid_amount,
            "message": bid.message,
            "status": bid.status,
            "created_at": timezone.localtime(bid.created_at).isoformat() if bid.created_at else None,
        }
        if is_owner or bid.status == Bid.STATUS_ACCEPTED:
            bid_data["bidder"] = _serialize_member_profile(bid.bidder)
        results.append(bid_data)

    return JsonResponse({
        "item_id": item_id,
        "bidding_enabled": item.bidding_enabled,
        "bids": results,
        "is_owner": is_owner
    })


@csrf_exempt
def api_manage_bid(request, bid_id):
    """API to accept/reject a bid (owner only)"""
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    try:
        bid = Bid.objects.get(id=bid_id)
    except Bid.DoesNotExist:
        return JsonResponse({"detail": "Bid not found"}, status=404)

    if bid.marketplace_item.created_by != member:
        return JsonResponse({"detail": "You can only manage bids on your own items"}, status=403)

    action = request.POST.get("action")

    if action == "accept":
        bid.status = Bid.STATUS_ACCEPTED
        bid.is_winner = True
        bid.save()
        
        # Send winner email notification
        email_sent = send_winner_email(bid)
        
        if email_sent:
            return JsonResponse({
                "success": True, 
                "message": "Bid accepted! Winner has been notified via email.", 
                "status": bid.status,
                "winner_notified": True
            })
        else:
            return JsonResponse({
                "success": True, 
                "message": "Bid accepted! (Could not send email notification)", 
                "status": bid.status,
                "winner_notified": False
            })
    elif action == "reject":
        bid.status = Bid.STATUS_REJECTED
        bid.save()
        return JsonResponse({"success": True, "message": "Bid rejected", "status": bid.status})
    else:
        return JsonResponse({"detail": "Invalid action. Use 'accept' or 'reject'"}, status=400)

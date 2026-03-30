from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q, Max
import os

from .models import GalleryAlbum, GalleryImage, GoogleDriveConnection
from .google_drive_utils import get_drive_service, upload_file_to_drive, delete_file_from_drive, create_folder
from django.urls import reverse

from member.models import Member


STATUS_CODE_MAP = {
    "inreview": 0,
    "published": 1,
    "rejected": 2,
    "draft": 3,
}


def _gallery_image_name(album_pk, original_name, counter=1):
    ext = os.path.splitext(original_name or "")[1].lower() or ".jpg"
    return f"image{album_pk}_{counter}{ext}"


def _get_drive_proxy_url(file_id):
    if not file_id:
        return None
    base = getattr(settings, "BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")
    rel_path = reverse('gallery:drive_image_serve', kwargs={'file_id': file_id})
    return f"{base}{rel_path}"

def _get_image_display_url(gallery_image):
    if gallery_image.google_drive_file_id:
        return _get_drive_proxy_url(gallery_image.google_drive_file_id)
    return _public_media_url(gallery_image.image.url) if gallery_image.image else None

def _get_album_cover_url(album):
    if album.google_drive_file_id:
        return _get_drive_proxy_url(album.google_drive_file_id)
    return _public_media_url(album.cover_image.url) if album.cover_image else None

def _public_media_url(file_url):
    base = getattr(settings, "MEDIA_BASE_URL", settings.MEDIA_URL)
    normalized = (file_url or "").lstrip("/")
    return f"{base.rstrip('/')}/{normalized}"


def _serialize_album(album, include_images=False, request_member=None, include_all_images=False, request=None):
    """Serialize album data for JSON response"""
    created_by_name = None
    if album.member:
        if hasattr(album.member, "get_full_name"):
            created_by_name = album.member.get_full_name() or None
        if not created_by_name:
            created_by_name = getattr(album.member, "username", None) or str(album.member)
    
    publish_dt = album.published_at or album.updated_at or album.created_at
    
    is_owner = request_member and album.member_id == request_member.member_no
    if include_all_images or is_owner:
        image_count = album.all_image_count
    else:
        image_count = album.image_count
    
    data = {
        "id": album.id,
        "title": album.title,
        "slug": album.slug,
        "description": album.description,
        "cover_image_url": request.build_absolute_uri(album.display_url) if request and album.display_url else album.display_url,
        "visibility": album.visibility,
        "visibility_label": album.get_visibility_display(),
        "status": album.status,
        "status_code": STATUS_CODE_MAP.get(album.status),
        "status_label": album.get_status_display(),
        "member_id": album.member_id,
        "created_by_name": created_by_name,
        "image_count": image_count,
        "created_at": timezone.localtime(album.created_at).isoformat() if album.created_at else None,
        "updated_at": timezone.localtime(album.updated_at).isoformat() if album.updated_at else None,
        "published_at": timezone.localtime(publish_dt).isoformat() if publish_dt else None,
    }
    
    if include_images:
        if include_all_images or is_owner:
            images = album.images.all().order_by("order", "created_at")
        else:
            images = album.images.filter(status="published").order_by("order", "created_at")
            
            # Apply image visibility filtering
            if request_member: # Logged in but not owner
                images = images.exclude(visibility="private")
            else: # Anonymous
                images = images.exclude(visibility__in=["private", "protected"])
        
        data["images"] = [
            {
                "id": img.id,
                "title": img.title,
                "description": img.description,
                "image_url": request.build_absolute_uri(img.display_url) if request and img.display_url else img.display_url,
                "order": img.order,
                "status": img.status,
                "visibility": img.visibility,
                "visibility_label": img.get_visibility_display(),
                "created_at": timezone.localtime(img.created_at).isoformat() if img.created_at else None,
            }
            for img in images
        ]
        data["image_count"] = len(data["images"])
    
    return data


def get_logged_in_member(request):
    member_no = request.session.get('member_no')
    if not member_no:
        return None
    try:
        return Member.objects.get(member_no=member_no)
    except Member.DoesNotExist:
        return None


def my_albums(request):
    member = get_logged_in_member(request)
    if not member:
        return redirect('member:customer_login')

    from gallery.models import GoogleDriveConnection
    from gallery.google_drive_utils import get_drive_service
    
    connection = GoogleDriveConnection.objects.filter(member=member).first()
    drive_connected = bool(connection and connection.credentials_data)
    folder_exists = False
    
    if drive_connected and connection.folder_id:
        try:
            service = get_drive_service(connection)
            if service:
                # Check if folder exists and is not trashed
                folder_meta = service.files().get(
                    fileId=connection.folder_id, 
                    fields='id, trashed'
                ).execute()
                folder_exists = not folder_meta.get('trashed', False)
        except Exception:
            folder_exists = False

    published_albums = GalleryAlbum.objects.filter(status="published", member=member)
    unpublished_albums = GalleryAlbum.objects.exclude(status="published").filter(member=member)

    return render(request, "html_member/html_gallery/album_list.html", {
        "published_albums": published_albums,
        "unpublished_albums": unpublished_albums,
        "member": member,
        "drive_connected": drive_connected,
        "folder_exists": folder_exists,
        "folder_id": connection.folder_id if connection else None,

    })


def album_form(request, pk=None):
    member = get_logged_in_member(request)
    if not member:
        return redirect('member:customer_login')

    album = get_object_or_404(GalleryAlbum, pk=pk, member=member) if pk else None

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        visibility = request.POST.get("visibility", "public")
        action = (request.POST.get("action") or "").strip().lower()
        cover_image = request.FILES.get("cover_image")

        if album:
            previous_status = album.status
            if action == "save_draft":
                status = "draft"
            elif action == "submit_review":
                status = "inreview"
            else:
                status = "inreview" if previous_status in {"published", "rejected", "inreview"} else "draft"

            if previous_status in {"published", "rejected"}:
                status = "inreview"

            album.title = title
            album.description = description
            album.visibility = visibility
            album.status = status

            if cover_image:
                if album.cover_image:
                    album.cover_image.delete(save=False)
                album.cover_image.save(_gallery_image_name(album.pk, cover_image.name), cover_image, save=False)

            if status == "published" and (previous_status != "published" or not album.published_at):
                album.published_at = timezone.now()
            elif status != "published":
                album.published_at = None

            album.save()
            # Google Drive Integration: Update cover image on Drive
            if cover_image:
                connection = GoogleDriveConnection.objects.filter(member=member).first()
                if connection and connection.folder_id:
                    service = get_drive_service(connection)
                    if service:
                        # Ensure album folder exists
                        if not album.drive_folder_id:
                            album.drive_folder_id = create_folder(service, album.title, connection.folder_id)
                            album.save()
                            
                        # Delete old cover and upload new
                        if album.google_drive_file_id:
                            delete_file_from_drive(service, album.google_drive_file_id)
                        
                        # Reset pointer before upload
                        if hasattr(album.cover_image, 'seek'):
                            album.cover_image.seek(0)
                            
                        drive_file_id = upload_file_to_drive(service, album.cover_image, album.drive_folder_id)
                        album.google_drive_file_id = drive_file_id
                        album.save()
                        
                        # DELETE LOCAL COPY after successful upload
                        if album.cover_image:
                            local_path = album.cover_image.path
                            if os.path.exists(local_path):
                                os.remove(local_path)

        else:
            status = "inreview" if action == "submit_review" else "draft"
            created_album = GalleryAlbum.objects.create(
                title=title,
                description=description,
                visibility=visibility,
                status=status,
                cover_image=None,
                member=member,
                published_at=timezone.now() if status == "published" else None,
            )
            if cover_image:
                created_album.cover_image.save(
                    _gallery_image_name(created_album.pk, cover_image.name),
                    cover_image,
                    save=True,
                )
                # Google Drive Integration: Upload cover to Drive
                connection = GoogleDriveConnection.objects.filter(member=member).first()
                if connection and connection.folder_id:
                    service = get_drive_service(connection)
                    if service:
                        # Create album-specific folder
                        album_folder_id = create_folder(service, created_album.title, connection.folder_id)
                        created_album.drive_folder_id = album_folder_id
                        
                        # Reset pointer before upload
                        if hasattr(created_album.cover_image, 'seek'):
                            created_album.cover_image.seek(0)
                            
                        drive_file_id = upload_file_to_drive(service, created_album.cover_image, album_folder_id)
                        created_album.google_drive_file_id = drive_file_id
                        created_album.save()
                        
                        # DELETE LOCAL COPY
                        if created_album.cover_image:
                            try:
                                local_path = created_album.cover_image.path
                                if os.path.exists(local_path):
                                    # Ensure handle is closed
                                    if hasattr(created_album.cover_image, 'close'):
                                        created_album.cover_image.close()
                                    os.remove(local_path)
                            except Exception as e:
                                print(f"Error deleting local cover: {e}")


        return redirect("gallery:my_albums")

    return render(request, "html_member/html_gallery/album_form.html", {
        "album": album,
        "visibility_choices": GalleryAlbum.VISIBILITY_CHOICES,
        "status_choices": GalleryAlbum.STATUS_CHOICES,
    })


def album_add_images(request, pk):
    member = get_logged_in_member(request)
    if not member:
        return redirect('member:customer_login')

    album = get_object_or_404(GalleryAlbum, pk=pk, member=member)

    if request.method == "POST":
        images = request.FILES.getlist("images")
        titles = request.POST.getlist("title")
        batch_visibility = request.POST.get("batch_visibility", "public")
        
        for idx, image in enumerate(images):
            title = titles[idx] if idx < len(titles) else None
            max_order = album.images.aggregate(Max("order"))["order__max"] or 0
            gallery_image = GalleryImage.objects.create(
                album=album,
                image=image,
                title=title,
                visibility=batch_visibility,
                order=max_order + idx + 1,
                status="inreview"  # Images go to inreview when added
            )
            # Google Drive Integration: Upload to Drive
            connection = GoogleDriveConnection.objects.filter(member=member).first()
            if connection and connection.folder_id:
                service = get_drive_service(connection)
                if service:
                    # Ensure album folder exists
                    if not album.drive_folder_id:
                        album.drive_folder_id = create_folder(service, album.title, connection.folder_id)
                        album.save()
                        
                    drive_file_id = upload_file_to_drive(service, image, album.drive_folder_id)
                    gallery_image.google_drive_file_id = drive_file_id
                    gallery_image.save()
                    
                    # DELETE LOCAL COPY
                    if gallery_image.image:
                        try:
                            local_path = gallery_image.image.path
                            if os.path.exists(local_path):
                                # Ensure handle is closed
                                if hasattr(gallery_image.image, 'close'):
                                    gallery_image.image.close()
                                os.remove(local_path)
                        except Exception as e:
                            print(f"Error deleting local image: {e}")

        
        # FIX #2: Only change album status if it's draft (first submission)
        # If album is already published, keep it published - only new images go for review
        if album.status == "draft":
            album.status = "inreview"
            album.save()
        
        return JsonResponse({
            "success": True,
            "message": f"{len(images)} images added successfully. New images are pending review.",
            "image_count": album.image_count,
            "album_status": album.status
        })

    return render(request, "html_member/html_gallery/image_upload.html", {
        "album": album,
    })


def album_submit_review(request, pk):
    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    album = get_object_or_404(GalleryAlbum, pk=pk, member=member)
    
    if album.status == "published":
        return JsonResponse({"detail": "Album is already published"}, status=400)
    
    album.status = "inreview"
    album.save()
    
    return JsonResponse({
        "success": True,
        "message": "Album submitted for review",
        "status": album.status
    })


def album_delete(request, pk):
    member = get_logged_in_member(request)
    if not member:
        return redirect('member:customer_login')

    album = get_object_or_404(GalleryAlbum, pk=pk, member=member)
    
    # Google Drive Integration: Delete album folder from Drive
    connection = GoogleDriveConnection.objects.filter(member=member).first()
    service = get_drive_service(connection) if connection else None

    if service:
        if album.drive_folder_id:
            delete_file_from_drive(service, album.drive_folder_id)
        elif album.google_drive_file_id:
            # Fallback for old albums
            delete_file_from_drive(service, album.google_drive_file_id)
    
    for image in album.images.all():
        if image.google_drive_file_id and service:
            delete_file_from_drive(service, image.google_drive_file_id)

        if image.image:
            image.image.delete(save=False)
    
    if album.cover_image:
        album.cover_image.delete(save=False)
    
    album.delete()
    
    return redirect("gallery:my_albums")


def api_delete_image(request, pk):
    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    image = get_object_or_404(GalleryImage, pk=pk, album__member=member)
    album = image.album
    
    if image.image:
        image.image.delete(save=False)
    
    # Google Drive Integration: Delete image from Drive
    if image.google_drive_file_id:
        connection = GoogleDriveConnection.objects.filter(member=member).first()
        if connection:
            service = get_drive_service(connection)
            if service:
                delete_file_from_drive(service, image.google_drive_file_id)
    
    image.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            "success": True,
            "message": "Image deleted",
            "image_count": album.image_count
        })
    
    return redirect("gallery:album_add_images", pk=album.pk)


def api_all_albums(request):
    import logging
    logger = logging.getLogger(__name__)
    
    ordering_mode = "-published_at"
    
    is_logged_in = request.GET.get("logged_in") == "true"
    request_username = request.GET.get("username", "").strip()

    current_member = None
    if is_logged_in and request_username:
        # Load the member for the serializer
        current_member = Member.objects.filter(username=request_username).first()

    logger.warning(f"GALLERY: logged_in={is_logged_in}, username={request_username}")

    albums_qs = GalleryAlbum.objects.filter(status="published").select_related("member").order_by("-published_at", "-id")

    visible_albums = []
    for album in albums_qs:
        # Check if current user is the owner
        is_owner = is_logged_in and request_username and album.member and (album.member.username == request_username)
        
        logger.warning(f"GALLERY: album={album.title}, visibility={album.visibility}, is_owner={is_owner}")
        
        # Owner can always see their own albums regardless of visibility
        if is_owner:
            visible_albums.append(album)
            logger.warning(f"GALLERY: added (owner): {album.title}")
        # Public albums visible to everyone (including non-logged in)
        elif album.visibility == "public":
            visible_albums.append(album)
            logger.warning(f"GALLERY: added (public): {album.title}")
        # Protected albums visible only to logged-in users (not owner - handled above)
        elif album.visibility == "protected":
            if is_logged_in:
                visible_albums.append(album)
                logger.warning(f"GALLERY: added (protected): {album.title}")
        # Private albums - only owner can see (already handled above)
        # No else needed - private albums only visible to owner
    
    logger.warning(f"GALLERY: visible count = {len(visible_albums)}")

    requested_id = (request.GET.get("id") or "").strip()
    requested_slug = (request.GET.get("slug") or "").strip()

    if requested_id:
        try:
            requested_id = int(requested_id)
        except ValueError:
            return JsonResponse({"detail": "Invalid id value"}, status=400)

        album = next((a for a in visible_albums if a.id == requested_id), None)
        if not album:
            return JsonResponse({"detail": "Album not found", "id": requested_id}, status=404)
        
        return JsonResponse({
            "result": _serialize_album(album, include_images=True, request_member=current_member, request=request)
        })

    if requested_slug:
        album = next((a for a in visible_albums if a.slug == requested_slug), None)
        if not album:
            return JsonResponse({"detail": "Album not found", "slug": requested_slug}, status=404)
        
        return JsonResponse({
            "result": _serialize_album(album, include_images=True, request_member=current_member)
        })

    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size") or request.GET.get("per_page") or 12
    try:
        page_size = max(1, int(page_size))
    except (TypeError, ValueError):
        page_size = 12

    paginator = Paginator(visible_albums, page_size)
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages) if paginator.num_pages else []
    except Exception:
        page_obj = paginator.page(1) if paginator.num_pages else []

    results = []
    iterable = page_obj.object_list if paginator.num_pages else []
    for album in iterable:
        results.append(_serialize_album(album, include_images=True, request_member=current_member, request=request))

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

    return JsonResponse(
        {
            "count": paginator.count,
            "page": current_page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_previous": has_previous,
            "ordering": ordering_mode,
            "results": results,
        }
    )


def api_my_albums(request):
    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    albums = GalleryAlbum.objects.filter(member=member).order_by("-created_at")
    results = [_serialize_album(album, include_images=True, request_member=member, include_all_images=True, request=request) for album in albums]
    
    return JsonResponse({
        "count": len(results),
        "results": results
    })


def api_create_album(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    import json
    try:
        data = json.loads(request.body)
    except:
        data = request.POST.dict()

    title = data.get("title")
    description = data.get("description", "")
    visibility = data.get("visibility", "public")

    if not title:
        return JsonResponse({"detail": "Title is required"}, status=400)

    album = GalleryAlbum.objects.create(
        title=title,
        description=description,
        visibility=visibility,
        status="draft",
        member=member,
    )
    # Google Drive Integration: Create album folder
    connection = GoogleDriveConnection.objects.filter(member=member).first()
    if connection and connection.folder_id:
        service = get_drive_service(connection)
        if service:
            album_folder_id = create_folder(service, album.title, connection.folder_id)
            album.drive_folder_id = album_folder_id
            album.save()


    return JsonResponse({
        "success": True,
        "album": _serialize_album(album)
    })


def api_add_images_to_album(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    album = get_object_or_404(GalleryAlbum, pk=pk, member=member)
    
    images = request.FILES.getlist("images")
    if not images:
        return JsonResponse({"detail": "No images provided"}, status=400)

    created_images = []
    max_order = album.images.aggregate(Max("order"))["order__max"] or 0
    batch_visibility = request.POST.get("visibility", "public")
    
    for idx, image in enumerate(images):
        gallery_image = GalleryImage.objects.create(
            album=album,
            image=image,
            visibility=batch_visibility,
            order=max_order + idx + 1,
            status="inreview"  # Images go to inreview
        )
        # Google Drive Integration: Upload to Drive
        connection = GoogleDriveConnection.objects.filter(member=member).first()
        if connection and connection.folder_id:
            service = get_drive_service(connection)
            if service:
                # Ensure album folder exists
                if not album.drive_folder_id:
                    album.drive_folder_id = create_folder(service, album.title, connection.folder_id)
                    album.save()
                    
                # Reset pointer before upload
                if hasattr(image, 'seek'):
                    image.seek(0)
                
                drive_file_id = upload_file_to_drive(service, image, album.drive_folder_id)
                gallery_image.google_drive_file_id = drive_file_id
                gallery_image.save()
                
                # DELETE LOCAL COPY after successful upload
                if gallery_image.image:
                    try:
                        local_path = gallery_image.image.path
                        if os.path.exists(local_path):
                            # Ensure handle is closed
                            if hasattr(gallery_image.image, 'close'):
                                gallery_image.image.close()
                            os.remove(local_path)
                    except Exception as e:
                        print(f"Error deleting local image: {e}")
        
        created_images.append({
            "id": gallery_image.id,
            "image_url": gallery_image.display_url,

            "order": gallery_image.order,
            "visibility": gallery_image.visibility
        })

    # FIX #2: Only change album status if it's draft
    if album.status == "draft":
        album.status = "inreview"
        album.save()

    return JsonResponse({
        "success": True,
        "message": f"{len(created_images)} images added",
        "images": created_images,
        "image_count": album.image_count
    })


def api_update_album(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    album = get_object_or_404(GalleryAlbum, pk=pk, member=member)
    
    import json
    try:
        data = json.loads(request.body)
    except:
        data = request.POST.dict()

    title = data.get("title")
    description = data.get("description")
    visibility = data.get("visibility")

    if title:
        album.title = title
    if description is not None:
        album.description = description
    if visibility:
        album.visibility = visibility
    
    album.save()

    return JsonResponse({
        "success": True,
        "album": _serialize_album(album)
    })


def api_delete_album(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    album = get_object_or_404(GalleryAlbum, pk=pk, member=member)
    
    # Google Drive Integration: Delete album folder from Drive
    connection = GoogleDriveConnection.objects.filter(member=member).first()
    service = get_drive_service(connection) if connection else None
    
    if service:
        if album.drive_folder_id:
            delete_file_from_drive(service, album.drive_folder_id)
        elif album.google_drive_file_id:
            # Fallback for old albums
            delete_file_from_drive(service, album.google_drive_file_id)
            
    for image in album.images.all():
        if image.image:
            image.image.delete(save=False)
    if album.cover_image:
        album.cover_image.delete(save=False)
    
    album.delete()

    album.delete()

    return JsonResponse({
        "success": True,
        "message": "Album deleted"
    })

def api_update_image_visibility(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    image = get_object_or_404(GalleryImage, pk=pk, album__member=member)
    
    import json
    try:
        data = json.loads(request.body)
    except:
        data = request.POST.dict()

    visibility = data.get("visibility")
    
    if visibility in ["public", "protected", "private"]:
        image.visibility = visibility
        image.save()
        return JsonResponse({
            "success": True, 
            "message": "Visibility updated", 
            "visibility": image.visibility,
            "visibility_label": image.get_visibility_display()
        })
        
    return JsonResponse({"detail": "Invalid visibility value"}, status=400)


def api_admin_pending_albums(request):
    if not request.user.is_superuser:
        return JsonResponse({"detail": "Admin access required"}, status=403)

    albums = GalleryAlbum.objects.filter(status="inreview").select_related("member").order_by("-created_at")
    results = [_serialize_album(album) for album in albums]

    return JsonResponse({
        "count": len(results),
        "results": results
    })


def api_admin_review_album(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    if not request.user.is_superuser:
        return JsonResponse({"detail": "Admin access required"}, status=403)

    album = get_object_or_404(GalleryAlbum, pk=pk)
    
    import json
    try:
        data = json.loads(request.body)
    except:
        data = request.POST.dict()

    action = data.get("action")

    if action == "publish":
        album.status = "published"
        album.published_at = timezone.now()
        album.save()
        return JsonResponse({
            "success": True,
            "message": "Album published successfully",
            "status": album.status
        })
    elif action == "reject":
        album.status = "rejected"
        album.save()
        return JsonResponse({
            "success": True,
            "message": "Album rejected",
            "status": album.status
        })
    else:
        return JsonResponse({"detail": "Invalid action. Use 'publish' or 'reject'"}, status=400)


def api_admin_pending_images(request):
    """Get images pending review across all albums"""
    if not request.user.is_superuser:
        return JsonResponse({"detail": "Admin access required"}, status=403)

    images = GalleryImage.objects.filter(status="inreview").select_related("album", "album__member").order_by("-created_at")

    results = []
    for img in images:
        results.append({
            "id": img.id,
            "album_id": img.album_id,
            "album_title": img.album.title,
            "member_id": img.album.member_id,
            "member_name": img.album.member.username if img.album.member else None,
            "title": img.title,
            "image_url": img.display_url,
            "order": img.order,
            "status": img.status,
            "created_at": timezone.localtime(img.created_at).isoformat() if img.created_at else None,
        })

    return JsonResponse({
        "count": len(results),
        "results": results
    })


def api_admin_review_image(request, pk):
    """Review (publish/reject) individual image"""
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    if not request.user.is_superuser:
        return JsonResponse({"detail": "Admin access required"}, status=403)

    image = get_object_or_404(GalleryImage, pk=pk)
    
    import json
    try:
        data = json.loads(request.body)
    except:
        data = request.POST.dict()

    action = data.get("action")

    if action == "publish":
        image.status = "published"
        image.published_at = timezone.now()
        image.save()
        return JsonResponse({
            "success": True,
            "message": "Image published successfully",
            "status": image.status
        })
    elif action == "reject":
        image.status = "rejected"
        image.save()
        return JsonResponse({
            "success": True,
            "message": "Image rejected",
            "status": image.status
        })
    else:
        return JsonResponse({"detail": "Invalid action. Use 'publish' or 'reject'"}, status=400)

import json
import io

from django.conf import settings
from django.contrib import messages
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from googleapiclient.http import MediaIoBaseDownload

from gallery.google_drive_utils import create_careers_folder, create_folder, delete_file_from_drive, get_drive_service, upload_file_to_drive
from gallery.models import GoogleDriveConnection
from member.models import Member

from .forms import CareerPostForm
from .models import CareerPost


def get_logged_in_member(request):
    member_no = request.session.get("member_no")
    if not member_no:
        return None
    try:
        return Member.objects.get(member_no=member_no)
    except Member.DoesNotExist:
        return None


def _get_drive_proxy_url(file_id):
    if not file_id:
        return None
    base = getattr(settings, "BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")
    rel_path = reverse("career:career_document_serve", kwargs={"file_id": file_id})
    return f"{base}{rel_path}"


def _get_drive_image_proxy_url(file_id):
    if not file_id:
        return None
    base = getattr(settings, "BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")
    rel_path = reverse("career:career_image_serve", kwargs={"file_id": file_id})
    return f"{base}{rel_path}"


def _serialize_career_post(item):
    contact_name = item.full_name or item.created_by_name or "Unknown"
    document_view_url = _get_drive_proxy_url(item.document_drive_file_id)
    document_download_url = f"{document_view_url}?download=1" if document_view_url else None
    image_url = _get_drive_image_proxy_url(item.image_drive_file_id)
    return {
        "id": item.id,
        "post_type": item.post_type,
        "post_type_label": item.get_post_type_display(),
        "title": item.title,
        "job_title": item.job_title,
        "description": item.description,
        "full_name": contact_name,
        "email": item.email,
        "phone": item.phone,
        "location": item.location,
        "contact_person_name": item.contact_person_name,
        "contact_person_number": item.contact_person_number,
        "company_name": item.company_name,
        "current_company_name": item.current_company_name,
        "responsibilities": item.responsibilities,
        "skills": item.skills,
        "current_ctc_lpa": item.current_ctc_lpa,
        "expected_lpa": item.expected_lpa,
        "package_lpa": item.package_lpa,
        "experience_years": item.experience_years,
        "enable_compensation": item.enable_compensation,
        "enable_document": item.enable_document,
        "document_filename": item.document_filename,
        "document_url": document_view_url,
        "document_download_url": document_download_url,
        "image_url": image_url,
        "image_filename": item.image_filename,
        "status": item.status,
        "status_label": item.get_status_display(),
        "created_at": timezone.localtime(item.created_at).isoformat() if item.created_at else None,
        "published_at": timezone.localtime(item.published_at).isoformat() if item.published_at else None,
    }


def member_career_list(request):
    member = get_logged_in_member(request)
    if not member:
        return redirect("/member/login/")

    posts_qs = CareerPost.objects.filter(created_by=member).order_by("-created_at")
    search_query = (request.GET.get("q") or "").strip()
    if search_query:
        posts_qs = posts_qs.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(company_name__icontains=search_query)
            | Q(skills__icontains=search_query)
            | Q(location__icontains=search_query)
        )

    published_posts = posts_qs.filter(status=CareerPost.STATUS_PUBLISHED)
    unpublished_posts = posts_qs.exclude(status=CareerPost.STATUS_PUBLISHED)

    return render(
        request,
        "html_member/html_career/career_list.html",
        {
            "published_posts": published_posts,
            "unpublished_posts": unpublished_posts,
        },
    )


def member_career_form(request, pk=None):
    member = get_logged_in_member(request)
    if not member:
        return redirect("/member/login/")

    item = get_object_or_404(CareerPost, pk=pk, created_by=member) if pk else None

    if request.method == "POST":
        form = CareerPostForm(request.POST, instance=item)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.job_title = obj.title
            obj.enable_compensation = True
            obj.enable_document = True
            if obj.post_type == CareerPost.POST_TYPE_RECRUITER:
                if not obj.company_name:
                    form.add_error("company_name", "Company name is required for recruiter posts.")
                if not obj.contact_person_name:
                    form.add_error("contact_person_name", "Contact person name is required for recruiter posts.")
                if not obj.contact_person_number:
                    form.add_error("contact_person_number", "Contact person number is required for recruiter posts.")
            else:
                if not obj.current_company_name:
                    form.add_error("current_company_name", "Current company name is required for job seeker posts.")
                if not obj.skills:
                    form.add_error("skills", "Skills are required for job seeker posts.")

            if form.errors:
                return render(
                    request,
                    "html_member/html_career/career_form.html",
                    {
                        "form": form,
                        "item": item,
                        "member": member,
                    },
                )

            action = (request.POST.get("action") or "").strip().lower()
            previous_status = item.status if item else None

            if action == "save_draft":
                status = CareerPost.STATUS_DRAFT
            elif action == "submit_review":
                status = CareerPost.STATUS_INREVIEW
            else:
                status = previous_status or CareerPost.STATUS_DRAFT

            if previous_status in {CareerPost.STATUS_PUBLISHED, CareerPost.STATUS_REJECTED}:
                status = CareerPost.STATUS_INREVIEW

            member_name = f"{member.first_name} {member.surname}".strip() or member.username
            obj.created_by = member
            obj.created_by_name = member_name
            obj.status = status

            uploaded_pdf = request.FILES.get("resume_pdf") or request.FILES.get("jd_pdf")
            uploaded_image = request.FILES.get("profile_image") or request.FILES.get("company_image")
            if uploaded_pdf:
                connection = GoogleDriveConnection.objects.filter(member=member).first()
                if not (connection and connection.folder_id):
                    messages.error(request, "Google Drive not connected. Connect it from Gallery first, then upload PDF.")
                    return render(
                        request,
                        "html_member/html_career/career_form.html",
                        {
                            "form": form,
                            "item": item,
                            "member": member,
                        },
                    )

                service = get_drive_service(connection)
                if not service:
                    messages.error(request, "Could not connect to Google Drive. Please reconnect and try again.")
                    return render(
                        request,
                        "html_member/html_career/career_form.html",
                        {
                            "form": form,
                            "item": item,
                            "member": member,
                        },
                    )

                career_root_id = create_careers_folder(service)
                type_folder_name = "recruiter" if obj.post_type == CareerPost.POST_TYPE_RECRUITER else "job_seeker"
                type_folder_id = create_folder(service, type_folder_name, career_root_id)
                documents_folder_id = create_folder(service, "documents", type_folder_id)

                if item and item.document_drive_file_id:
                    delete_file_from_drive(service, item.document_drive_file_id)

                drive_file_id = upload_file_to_drive(service, uploaded_pdf, documents_folder_id, filename=uploaded_pdf.name)
                obj.document_drive_file_id = drive_file_id
                obj.document_filename = uploaded_pdf.name

            if uploaded_image:
                connection = GoogleDriveConnection.objects.filter(member=member).first()
                if not (connection and connection.folder_id):
                    messages.error(request, "Google Drive not connected. Connect it from Gallery first, then upload image.")
                    return render(
                        request,
                        "html_member/html_career/career_form.html",
                        {
                            "form": form,
                            "item": item,
                            "member": member,
                        },
                    )

                service = get_drive_service(connection)
                if not service:
                    messages.error(request, "Could not connect to Google Drive. Please reconnect and try again.")
                    return render(
                        request,
                        "html_member/html_career/career_form.html",
                        {
                            "form": form,
                            "item": item,
                            "member": member,
                        },
                    )

                career_root_id = create_careers_folder(service)
                type_folder_name = "recruiter" if obj.post_type == CareerPost.POST_TYPE_RECRUITER else "job_seeker"
                type_folder_id = create_folder(service, type_folder_name, career_root_id)
                images_folder_id = create_folder(service, "images", type_folder_id)

                if item and item.image_drive_file_id:
                    delete_file_from_drive(service, item.image_drive_file_id)

                image_file_id = upload_file_to_drive(service, uploaded_image, images_folder_id, filename=uploaded_image.name)
                obj.image_drive_file_id = image_file_id
                obj.image_filename = uploaded_image.name

            obj.save()
            return redirect("career:member_career_list")
    else:
        initial = {}
        if not item:
            initial["post_type"] = CareerPost.POST_TYPE_JOB_SEEKER
        form = CareerPostForm(instance=item, initial=initial)

    return render(
        request,
        "html_member/html_career/career_form.html",
        {
            "form": form,
            "item": item,
            "member": member,
        },
    )


def member_career_delete(request, pk):
    member = get_logged_in_member(request)
    if not member:
        return redirect("/member/login/")

    item = get_object_or_404(CareerPost, pk=pk, created_by=member)
    if request.method == "POST":
        if item.document_drive_file_id:
            connection = GoogleDriveConnection.objects.filter(member=member).first()
            service = get_drive_service(connection) if connection else None
            if service:
                delete_file_from_drive(service, item.document_drive_file_id)
        if item.image_drive_file_id:
            connection = GoogleDriveConnection.objects.filter(member=member).first()
            service = get_drive_service(connection) if connection else None
            if service:
                delete_file_from_drive(service, item.image_drive_file_id)
        item.delete()
        return redirect("career:member_career_list")

    return render(
        request,
        "html_member/html_career/career_delete_confirm.html",
        {"item": item},
    )


def api_post_types(request):
    data = [
        {"key": key, "label": label}
        for key, label in CareerPost.POST_TYPE_CHOICES
    ]
    return JsonResponse({"count": len(data), "results": data})


def api_career_posts(request):
    post_type = (request.GET.get("post_type") or "all").strip().lower()
    search = (request.GET.get("search") or "").strip()

    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        page = 1

    try:
        page_size = int(request.GET.get("page_size", 12))
    except ValueError:
        page_size = 12

    page = max(page, 1)
    page_size = max(1, min(page_size, 100))

    queryset = CareerPost.objects.filter(status=CareerPost.STATUS_PUBLISHED)

    if post_type in {CareerPost.POST_TYPE_JOB_SEEKER, CareerPost.POST_TYPE_RECRUITER}:
        queryset = queryset.filter(post_type=post_type)

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(full_name__icontains=search)
            | Q(company_name__icontains=search)
            | Q(skills__icontains=search)
            | Q(location__icontains=search)
        )

    paginator = Paginator(queryset, page_size)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

    results = [_serialize_career_post(item) for item in page_obj.object_list]

    return JsonResponse(
        {
            "count": paginator.count,
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "results": results,
        }
    )


def api_career_post_detail(request, post_id):
    item = CareerPost.objects.filter(status=CareerPost.STATUS_PUBLISHED, id=post_id).first()
    if not item:
        return JsonResponse({"detail": "Career post not found"}, status=404)

    return JsonResponse({"result": _serialize_career_post(item)})


@csrf_exempt
def api_career_post_create(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    payload = {}
    content_type = (request.content_type or "").lower()

    if "application/json" in content_type:
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"detail": "Invalid JSON payload"}, status=400)
    else:
        payload = request.POST

    post_type = (payload.get("post_type") or "").strip().lower()
    title = (payload.get("title") or "").strip()
    job_title = (payload.get("job_title") or "").strip()
    description = (payload.get("description") or "").strip()
    full_name = (payload.get("full_name") or "").strip()
    email = (payload.get("email") or "").strip()
    phone = (payload.get("phone") or "").strip()
    location = (payload.get("location") or "").strip()
    company_name = (payload.get("company_name") or "").strip()
    current_company_name = (payload.get("current_company_name") or "").strip()
    contact_person_name = (payload.get("contact_person_name") or "").strip()
    contact_person_number = (payload.get("contact_person_number") or "").strip()
    responsibilities = (payload.get("responsibilities") or "").strip()
    skills = (payload.get("skills") or "").strip()
    current_ctc_lpa = (payload.get("current_ctc_lpa") or "").strip()
    expected_lpa = (payload.get("expected_lpa") or "").strip()
    package_lpa = (payload.get("package_lpa") or "").strip()
    experience_years = (payload.get("experience_years") or "").strip()

    valid_post_types = {choice[0] for choice in CareerPost.POST_TYPE_CHOICES}
    if post_type not in valid_post_types:
        return JsonResponse({"detail": "Invalid post type"}, status=400)

    if not title:
        return JsonResponse({"detail": "Title is required"}, status=400)

    if not description:
        return JsonResponse({"detail": "Description is required"}, status=400)

    if not email and not phone:
        return JsonResponse({"detail": "Provide email or phone"}, status=400)

    if post_type == CareerPost.POST_TYPE_RECRUITER:
        if not company_name:
            return JsonResponse({"detail": "Company name is required for recruiter post"}, status=400)
        if not contact_person_name or not contact_person_number:
            return JsonResponse({"detail": "Contact person name and number are required for recruiter post"}, status=400)
    else:
        if not current_company_name:
            return JsonResponse({"detail": "Current company name is required for job seeker post"}, status=400)
        if not skills:
            return JsonResponse({"detail": "Skills are required for job seeker post"}, status=400)

    full_name = full_name or (f"{member.first_name} {member.surname}".strip() or member.username)

    post = CareerPost.objects.create(
        post_type=post_type,
        title=title,
        job_title=job_title or title,
        description=description,
        full_name=full_name,
        email=email or None,
        phone=phone or None,
        location=location or None,
        contact_person_name=contact_person_name or None,
        contact_person_number=contact_person_number or None,
        company_name=company_name or None,
        current_company_name=current_company_name or None,
        responsibilities=responsibilities or None,
        skills=skills or None,
        current_ctc_lpa=current_ctc_lpa or None,
        expected_lpa=expected_lpa or None,
        package_lpa=package_lpa or None,
        experience_years=experience_years or None,
        status=CareerPost.STATUS_INREVIEW,
        created_by=member,
        created_by_name=full_name,
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Career post submitted for admin review",
            "post": _serialize_career_post(post),
        },
        status=201,
    )


@xframe_options_exempt
def serve_career_document(request, file_id):
    post = CareerPost.objects.filter(document_drive_file_id=file_id).select_related("created_by").first()
    if not post:
        return HttpResponse("Document not found", status=404)

    owner = post.created_by
    if not owner:
        return HttpResponse("Document owner not found", status=404)

    connection = GoogleDriveConnection.objects.filter(member=owner).first()
    service = get_drive_service(connection) if connection else None
    if not service:
        return HttpResponse("Could not access Google Drive", status=500)

    try:
        metadata = service.files().get(fileId=file_id, fields="mimeType, name").execute()
        file_name = metadata.get("name") or post.document_filename or "career_document.pdf"
        mime_type = metadata.get("mimeType") or "application/pdf"

        fh = io.BytesIO()
        request_obj = service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(fh, request_obj)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        content = fh.getvalue()
        response = HttpResponse(content, content_type=mime_type)
        if request.GET.get("download") == "1":
            response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        else:
            response["Content-Disposition"] = f'inline; filename="{file_name}"'
        return response
    except Exception as exc:
        return HttpResponse(f"Error fetching document: {exc}", status=500)


def serve_career_image(request, file_id):
    post = CareerPost.objects.filter(image_drive_file_id=file_id).select_related("created_by").first()
    if not post:
        return HttpResponse("Image not found", status=404)

    owner = post.created_by
    if not owner:
        return HttpResponse("Image owner not found", status=404)

    connection = GoogleDriveConnection.objects.filter(member=owner).first()
    service = get_drive_service(connection) if connection else None
    if not service:
        return HttpResponse("Could not access Google Drive", status=500)

    try:
        metadata = service.files().get(fileId=file_id, fields="mimeType, name").execute()
        mime_type = metadata.get("mimeType") or "image/jpeg"

        fh = io.BytesIO()
        request_obj = service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(fh, request_obj)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        content = fh.getvalue()
        return HttpResponse(content, content_type=mime_type)
    except Exception as exc:
        return HttpResponse(f"Error fetching image: {exc}", status=500)

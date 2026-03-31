import os
import json
from django.shortcuts import redirect
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, Http404, JsonResponse
from googleapiclient.http import MediaIoBaseDownload
import io
from google_auth_oauthlib.flow import Flow
from .models import GoogleDriveConnection, GalleryImage, GalleryAlbum
from .google_drive_utils import get_drive_service, create_gallery_folder, create_folder
from member.views import get_logged_in_member

# Scopes required for the application
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# For local development only
if settings.DEBUG:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def get_google_auth_flow(request):
    """Initializes the OAuth flow using client secrets from settings"""
    client_config = {
        "web": {
            "client_id": getattr(settings, "GOOGLE_DRIVE_CLIENT_ID", ""),
            "client_secret": getattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [getattr(settings, "GOOGLE_DRIVE_REDIRECT_URI", "")]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_DRIVE_REDIRECT_URI
    )
    return flow

def google_drive_auth_init(request):
    """Starts the Google Drive OAuth flow"""
    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    flow = get_google_auth_flow(request)
    
    # Generate the initial authorization URL to get the state and code_verifier
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Pack both into a single string for transport
    state_payload = json.dumps({
        "s": state,
        "v": flow.code_verifier,
        "m": member.member_no  # Backup identification
    })
    
    # Store in session as backup
    request.session['google_oauth_state_payload'] = state_payload
    
    # Re-generate the URL with our packed state
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=state_payload
    )
    
    return redirect(authorization_url)

def google_drive_callback(request):
    """Handles the callback from Google OAuth"""
    # Try to get member from session first
    member = get_logged_in_member(request)
    
    # Retrieve state parameter from URL
    state_param = request.GET.get('state')
    state_payload = None
    if state_param:
        try:
            state_payload = json.loads(state_param)
        except:
            pass

    # If session is lost (common on HTTP redirects), try to recover from state payload
    if not member and state_payload and 'm' in state_payload:
        from member.models import Member
        try:
            member = Member.objects.get(member_no=state_payload['m'])
            # LOG THE USER BACK IN
            request.session['member_no'] = member.member_no
            print(f"Session recovered from OAuth state for member {member.member_no}")
        except:
            pass

    if not member:
        print("Unauthorized: /gallery/google-drive/callback/ - Session clearly lost")
        return JsonResponse({"detail": "Authentication required"}, status=401)
    if not state_payload:
        # Fallback to session
        session_payload = request.session.get('google_oauth_state_payload')
        if session_payload:
            try:
                state_payload = json.loads(session_payload)
            except:
                pass

    if not state_payload:
        return JsonResponse({"detail": "Invalid state: Could not find session or state payload"}, status=400)

    code_verifier = state_payload.get('v')
    
    try:
        flow = get_google_auth_flow(request)
        flow.fetch_token(
            authorization_response=request.build_absolute_uri(),
            code_verifier=code_verifier
        )
        
        credentials = flow.credentials
        
        # Save or update connection
        connection, created = GoogleDriveConnection.objects.get_or_create(member=member)
        connection.set_credentials(credentials)
        connection.save()
        
        # Create the 'gallery' folder under NeighborNet if it doesn't exist
        service = get_drive_service(connection)
        folder_id = create_gallery_folder(service)
        connection.folder_id = folder_id
        connection.save()
        
        return redirect('gallery:my_albums')
    except Exception as e:
        return JsonResponse({"detail": f"Token exchange failed: {str(e)}"}, status=400)

def check_drive_connection(request):
    """Checks if the current member has a Google Drive connection and if folder still exists"""
    member = get_logged_in_member(request)
    if not member:
        return JsonResponse({"connected": False}, status=200)
    
    connection = GoogleDriveConnection.objects.filter(member=member).first()
    if not (connection and connection.credentials_data):
        return JsonResponse({"connected": False, "folder_id": None})
    
    # Check if folder actually exists on Drive
    folder_exists = False
    if connection.folder_id:
        try:
            service = get_drive_service(connection)
            if service:
                # Try to get the folder metadata
                # Note: if it's in trash, this might still work unless we check 'trashed'
                folder_meta = service.files().get(
                    fileId=connection.folder_id, 
                    fields='id, trashed'
                ).execute()
                folder_exists = not folder_meta.get('trashed', False)
        except Exception:
            # If we get an error (like 404), the folder is gone
            folder_exists = False
            
    return JsonResponse({
        "connected": True,
        "folder_id": connection.folder_id,
        "folder_exists": folder_exists,
        "error": "Root folder 'gallery' not found inside 'NeighborNet'. Please reconnect." if not folder_exists else None
    })

def serve_drive_image(request, file_id):
    """Proxies an image from Google Drive to the browser"""
    from gallery.models import GalleryAlbum, GalleryImage
    
    # Find the owner of this file to use their credentials
    owner = None
    album = GalleryAlbum.objects.filter(google_drive_file_id=file_id).first()
    if album:
        owner = album.member
    else:
        # Check images
        img = GalleryImage.objects.filter(google_drive_file_id=file_id).select_related('album__member').first()
        if img:
            owner = img.album.member
            
    if not owner:
        # Fallback to current user if for some reason not in DB
        owner = get_logged_in_member(request)
        
    if not owner:
        print(f"SERVE IMAGE: Unauthorized - No owner found for file {file_id}")
        return HttpResponse("Unauthorized", status=401)
        
    # Check if any service can see the file
    service = None
    can_see_file = False
    is_trashed = False
    
    # Try owner first
    connection = GoogleDriveConnection.objects.filter(member=owner).first()
    if connection:
        temp_service = get_drive_service(connection)
        if temp_service:
            try:
                meta = temp_service.files().get(fileId=file_id, fields='id, trashed').execute()
                can_see_file = True
                is_trashed = meta.get('trashed', False)
                service = temp_service
                if is_trashed:
                    print(f"SERVE IMAGE: File {file_id} found for {owner.username} but it is in TRASH.")
            except:
                pass
                
    # Fallback to other connections
    if not can_see_file:
        for other_conn in GoogleDriveConnection.objects.exclude(member=owner):
            temp_service = get_drive_service(other_conn)
            if not temp_service:
                continue
            try:
                meta = temp_service.files().get(fileId=file_id, fields='id, trashed').execute()
                can_see_file = True
                is_trashed = meta.get('trashed', False)
                service = temp_service
                print(f"SERVE IMAGE: File {file_id} found via {other_conn.member.username}'s connection! Trashed: {is_trashed}")
                break
            except:
                continue

    if not service or not can_see_file:
        print(f"SERVE IMAGE: Final Failure - File {file_id} not found/accessible by any connection.")
        return HttpResponse("File missing or inaccessible from Google Drive. Try restoring from Trash or re-uploading.", status=404)

    try:
        # Get file metadata to find mimetype and size
        file_metadata = service.files().get(fileId=file_id, fields='mimeType, name, size, shortcutDetails').execute()
        mimetype = file_metadata.get('mimeType', 'image/jpeg')
        size = file_metadata.get('size', '0')
        
        # Handle Shortcuts
        effective_file_id = file_id
        if mimetype == 'application/vnd.google-apps.shortcut':
            effective_file_id = file_metadata.get('shortcutDetails', {}).get('targetId', file_id)
            print(f"SERVE IMAGE: Resolving shortcut {file_id} -> {effective_file_id}")
            # Refresh metadata for the target
            file_metadata = service.files().get(fileId=effective_file_id, fields='mimeType, name, size').execute()
            mimetype = file_metadata.get('mimeType', 'image/jpeg')
            size = file_metadata.get('size', '0')

        print(f"SERVE IMAGE: Serving '{file_metadata.get('name')}' ({mimetype}, {size} bytes) for {owner.username}")
        
        # Download the file content using MediaIoBaseDownload (more robust for some file types)
        fh = io.BytesIO()
        request_obj = service.files().get_media(fileId=effective_file_id)
        downloader = MediaIoBaseDownload(fh, request_obj)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        image_content = fh.getvalue()
        
        if not image_content:
            print(f"SERVE IMAGE: WARNING - Downloaded content is EMPTY for {effective_file_id}. Metadata Size: {size}")
            return HttpResponse(f"Empty data from Drive (Size: {size})", status=404)
            
        return HttpResponse(image_content, content_type=mimetype)

    except Exception as e:
        print(f"Error serving Drive image {file_id}: {e}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Error: {e}", status=500)

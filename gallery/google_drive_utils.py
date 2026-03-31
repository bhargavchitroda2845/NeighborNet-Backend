import os
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from django.conf import settings


def _find_folder(service, name, parent_id=None):
    if parent_id:
        query = (
            f"name = '{name}' and '{parent_id}' in parents and "
            "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        )
    else:
        query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    return files[0]['id'] if files else None

def get_drive_service(connection):
    """Returns a Google Drive service object from a GoogleDriveConnection instance"""
    from google.auth.transport.requests import Request
    creds_dict = connection.get_credentials_dict()
    if not creds_dict:
        return None
    
    creds = Credentials(
        token=creds_dict.get('token'),
        refresh_token=creds_dict.get('refresh_token'),
        token_uri=creds_dict.get('token_uri'),
        client_id=creds_dict.get('client_id'),
        client_secret=creds_dict.get('client_secret'),
        scopes=creds_dict.get('scopes')
    )
    
    # Refresh the token if it's expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save the new credentials back to the connection
            connection.set_credentials(creds)
            connection.save()
        except Exception as e:
            print(f"Error refreshing Google Drive token: {e}")
            return None
    
    return build('drive', 'v3', credentials=creds)


def ensure_neighbornet_root_folder(service):
    """Creates/fetches the NeighborNet root folder in Drive."""
    existing_id = _find_folder(service, 'NeighborNet')
    if existing_id:
        return existing_id

    folder = service.files().create(
        body={
            'name': 'NeighborNet',
            'mimeType': 'application/vnd.google-apps.folder',
        },
        fields='id'
    ).execute()
    folder_id = folder.get('id')
    if folder_id:
        make_file_public(service, folder_id)
    return folder_id

def create_gallery_folder(service):
    """Creates/fetches NeighborNet/gallery and returns gallery folder ID."""
    root_id = ensure_neighbornet_root_folder(service)
    return create_folder(service, 'gallery', root_id)


def create_careers_folder(service):
    """Creates/fetches NeighborNet/careers and returns careers folder ID."""
    root_id = ensure_neighbornet_root_folder(service)
    return create_folder(service, 'careers', root_id)


def create_bb_album_folder(service):
    """Backward-compatible alias for NeighborNet/gallery folder."""
    return create_gallery_folder(service)


def create_bb_careers_folder(service):
    """Backward-compatible alias for NeighborNet/careers folder."""
    return create_careers_folder(service)

def create_folder(service, name, parent_id):
    """Creates a folder inside another folder and returns its ID"""
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    
    # Check if folder already exists in this parent
    query = f"name = '{name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    if files:
        return files[0]['id']
        
    folder = service.files().create(body=file_metadata, fields='id').execute()
    folder_id = folder.get('id')
    
    # Make folder public
    if folder_id:
        make_file_public(service, folder_id)
        
    return folder_id

def upload_file_to_drive(service, file_obj, folder_id, filename=None):
    """Uploads a file to a specific folder on Google Drive"""
    if not filename:
        filename = getattr(file_obj, 'name', 'uploaded_file')
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    # Ensure pointer is at start
    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)
        
    mimetype = getattr(file_obj, 'content_type', 'image/jpeg')
    media = MediaIoBaseUpload(file_obj, mimetype=mimetype, resumable=True)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webContentLink, thumbnailLink'
    ).execute()
    
    return file.get('id')

def make_file_public(service, file_id):
    """Sets the file/folder permission to 'anyone with the link can view'"""
    try:
        permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        service.permissions().create(fileId=file_id, body=permission).execute()
        return True
    except Exception as e:
        print(f"Error making file {file_id} public: {e}")
        return False

def delete_file_from_drive(service, file_id):
    """Deletes a file from Google Drive"""
    try:
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting file from Drive: {e}")
        return False

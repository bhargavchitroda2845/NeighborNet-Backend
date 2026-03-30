from django.urls import path
from . import views, google_drive_views
app_name = "gallery"


urlpatterns = [
    # Member URLs (HTML views)
    path('', views.my_albums, name='my_albums'),
    path('add/', views.album_form, name='album_add'),
    path('edit/<int:pk>/', views.album_form, name='album_edit'),
    path('delete/<int:pk>/', views.album_delete, name='album_delete'),
    path('<int:pk>/add-images/', views.album_add_images, name='album_add_images'),
    path('<int:pk>/submit-review/', views.album_submit_review, name='album_submit_review'),
    path('image/<int:pk>/visibility/', views.api_update_image_visibility, name='api_update_image_visibility'),
    path('image/<int:pk>/delete/', views.api_delete_image, name='api_delete_image'),
    
    # Google Drive URLs
    path('google-drive/connect/', google_drive_views.google_drive_auth_init, name='google_drive_connect'),
    path('google-drive/callback/', google_drive_views.google_drive_callback, name='google_drive_callback'),
    path('google-drive/status/', google_drive_views.check_drive_connection, name='google_drive_status'),
    path('drive-image/<str:file_id>/', google_drive_views.serve_drive_image, name='drive_image_serve'),
    
    # Public JSON APIs (for frontend)
    path('api/all/', views.api_all_albums, name='api_all_albums'),
    
    # Member JSON APIs (for React frontend)
    path('api/my/', views.api_my_albums, name='api_my_albums'),
    path('api/create/', views.api_create_album, name='api_create_album'),
    path('api/<int:pk>/update/', views.api_update_album, name='api_update_album'),
    path('api/<int:pk>/delete/', views.api_delete_album, name='api_delete_album'),
    path('api/<int:pk>/add-images/', views.api_add_images_to_album, name='api_add_images'),
    
    # Admin JSON APIs
    path('api/admin/pending/', views.api_admin_pending_albums, name='api_admin_pending'),
    path('api/admin/<int:pk>/review/', views.api_admin_review_album, name='api_admin_review'),
    # Admin Image Review APIs
    path('api/admin/images/pending/', views.api_admin_pending_images, name='api_admin_pending_images'),
    path('api/admin/images/<int:pk>/review/', views.api_admin_review_image, name='api_admin_review_image'),
]

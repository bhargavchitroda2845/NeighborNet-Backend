from django.urls import path

from . import views


app_name = "career"

urlpatterns = [
    path("member/career/", views.member_career_list, name="member_career_list"),
    path("member/career/add/", views.member_career_form, name="member_career_add"),
    path("member/career/<int:pk>/edit/", views.member_career_form, name="member_career_edit"),
    path("member/career/<int:pk>/delete/", views.member_career_delete, name="member_career_delete"),
    path("api/posts/", views.api_career_posts, name="api_career_posts"),
    path("api/posts/<int:post_id>/", views.api_career_post_detail, name="api_career_post_detail"),
    path("api/posts/create/", views.api_career_post_create, name="api_career_post_create"),
    path("api/post-types/", views.api_post_types, name="api_post_types"),
    path("drive-document/<str:file_id>/", views.serve_career_document, name="career_document_serve"),
    path("drive-image/<str:file_id>/", views.serve_career_image, name="career_image_serve"),
]

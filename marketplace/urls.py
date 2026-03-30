from django.urls import path
from . import views


app_name = "marketplace"

urlpatterns = [
    path("member/marketplace/", views.member_marketplace_list, name="member_marketplace_list"),
    path("member/marketplace/add/", views.member_marketplace_form, name="member_marketplace_add"),
    path("member/marketplace/<int:pk>/edit/", views.member_marketplace_form, name="member_marketplace_edit"),
    path("member/marketplace/<int:pk>/delete/", views.member_marketplace_delete, name="member_marketplace_delete"),
    path("member/marketplace/<int:pk>/bids/", views.member_marketplace_bids, name="member_marketplace_bids"),
    path("member/marketplace/bid/<int:pk>/<str:action>/", views.member_marketplace_bid_action, name="member_marketplace_bid_action"),
    path("api/marketplace/", views.api_all_marketplace, name="api_all_marketplace"),
    path("api/marketplace/listing-types/", views.api_listing_type_list, name="api_listing_type_list"),
    path("api/marketplace/sold-count/", views.api_sold_count, name="api_sold_count"),
    path("api/marketplace/<int:item_id>/bids/", views.api_get_bids, name="api_get_bids"),
    path("api/bid/place/", views.api_place_bid, name="api_place_bid"),
    path("api/bid/<int:bid_id>/manage/", views.api_manage_bid, name="api_manage_bid"),
]

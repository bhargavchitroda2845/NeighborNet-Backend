from django.urls import path

from . import views


app_name = "donation"

urlpatterns = [
    path("create/", views.donation_create, name="donation_create"),
    path("api/member-prefill/", views.member_prefill_api, name="member_prefill_api"),
    path("<int:donation_id>/voucher.pdf", views.donation_pdf, name="donation_pdf"),
]

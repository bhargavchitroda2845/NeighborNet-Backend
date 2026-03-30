from django.urls import path
from home import views

app_name = "home"
urlpatterns = [
    # ======================
    # CUSTOMER (NO LOGIN)
    # ======================
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),
    path('aboutus/', views.aboutus, name='about'),
    path('contact/', views.contact, name='contact'),

    # ======================
    # ADMIN (CUSTOM DASHBOARD)
    # ======================
    # path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
]

from django.urls import path
from . import views
app_name = "business"


urlpatterns = [
    path('', views.business_list, name='business_list'),
    path('add/', views.business_form, name='business_add'),
    path('edit/<int:pk>/', views.business_form, name='business_edit'),
    path('delete/<int:pk>/', views.business_delete, name='business_delete'),
    # Public JSON APIs
    path('categories/', views.api_category_list, name='api_category_list'),
    path('all/', views.api_all_business, name='api_all_business'),
]


from django.urls import path
from . import views
app_name = "news"



urlpatterns = [
    path('', views.news_list, name='news_list'),
    path('add/', views.news_form, name='news_add'),
    path('edit/<int:pk>/', views.news_form, name='news_edit'),
    path('delete/<int:pk>/', views.news_delete, name='news_delete'),
    # Public JSON APIs
    path('categories/', views.api_category_list, name='api_category_list'),
    path('allpost/', views.api_all_news, name='api_all_news'),
]

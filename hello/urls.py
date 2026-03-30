from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from member import views as member_views


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('home.urls')),
    path('member/', include('member.urls')),
    path('news/', include('news.urls')),
    path('', include('marketplace.urls')),
    path('donation/', include('donation.urls')),
    path('gallery/', include('gallery.urls')),
    path('business/', include('business.urls')),

    path('api/public/profile/', member_views.public_profile_api),
    path('api/master/countries/', member_views.country_list_api),
    path('api/master/states/', member_views.state_list_api),
    path('api/master/cities/', member_views.city_list_api),
    path('api/members/create/', member_views.member_create_api),
    path('api/members/pending/', member_views.pending_member_requests_api),
    path('api/members/<int:member_no>/approve/', member_views.approve_member_api),
    path('api/members/<int:member_no>/reject/', member_views.reject_member_api),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "BBAdmin Admin"
admin.site.site_title = "BBAdmin Admin Portal"
admin.site.index_title = "Welcome to BBAdmin App"


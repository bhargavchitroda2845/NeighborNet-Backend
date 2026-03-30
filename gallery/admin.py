from django.contrib import admin
from .models import GalleryAlbum, GalleryImage


class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 1
    fields = ('image', 'title', 'description', 'order', 'status')


@admin.register(GalleryAlbum)
class GalleryAlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'member', 'visibility', 'status', 'total_images', 'created_at')
    list_filter = ('status', 'visibility', 'created_at')
    search_fields = ('title', 'description', 'member__username', 'member__first_name', 'member__surname')
    readonly_fields = ('created_at', 'updated_at', 'published_at')
    inlines = [GalleryImageInline]
    
    def total_images(self, obj):
        """Return total number of images in the album"""
        return obj.all_image_count
    total_images.short_description = 'Total Images'


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'album', 'get_member', 'title', 'status', 'order', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description', 'album__title', 'album__member__username', 'album__member__first_name', 'album__member__surname')
    readonly_fields = ('created_at', 'published_at')
    
    def get_member(self, obj):
        """Return the member who owns the album"""
        if obj.album and obj.album.member:
            return obj.album.member
        return '-'
    get_member.short_description = 'Member'

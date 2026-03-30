from django.contrib import admin
from home.models import  Contact

# Register Contact
admin.site.register(Contact)

# Member admin
# @admin.register(Member)
# class MemberAdmin(admin.ModelAdmin):
#     def has_view_permission(self, request, obj=None):
#         return True
#     search_fields = ['member_no', 'first_name', 'surname']
#     list_display = ('member_no', 'first_name', 'surname', 'phone_no', 'status', 'created_at', 'updated_at')
#     list_filter = ('status', 'gender')


# MemberDetail admin


    # ordering = ['member_no']

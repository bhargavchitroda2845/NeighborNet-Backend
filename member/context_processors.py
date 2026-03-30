from .models import Member
from .models import MemberDetail


def sidebar_member(request):
    member_no = request.session.get("member_no")
    member = None
    if member_no:
        try:
            member = Member.objects.get(member_no=member_no)
        except Member.DoesNotExist:
            member = None
    sidebar_profile_image = None
    if member:
        if member.profile_image:
            sidebar_profile_image = member.profile_image.url
        else:
            latest_detail = (
                MemberDetail.objects
                .filter(member_no=member)
                .exclude(profile_image="")
                .order_by("-created_at")
                .first()
            )
            if latest_detail and latest_detail.profile_image:
                sidebar_profile_image = latest_detail.profile_image.url

    return {
        "sidebar_member": member,
        "sidebar_profile_image": sidebar_profile_image,
    }

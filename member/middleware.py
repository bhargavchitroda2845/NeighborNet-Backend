from django.shortcuts import redirect

class MemberAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        protected_paths = ['/member/dashboard/']

        if request.path in protected_paths:
            if not request.session.get('member_no'):
                return redirect('/member/login/')

        response = self.get_response(request)
        return response

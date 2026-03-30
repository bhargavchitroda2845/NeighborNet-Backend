from django.shortcuts import render
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from datetime import datetime
from .models import Contact
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.conf import settings


# =========================
# CUSTOMER VIEWS (PORT 8000)
# NO LOGIN REQUIRED
# =========================
# api_view(['GET'])
def index(request):
   return HttpResponseRedirect(settings.FRONTEND_BASE_URL)
    # return render(request, "html_home/index.html")






def home(request):
    return render(request, "html_home/home.html")


def aboutus(request):
    return render(request, "html_home/about.html")


def contact(request):
    if request.method == "POST":
        Contact.objects.create(
            name=request.POST.get("name"),
            email=request.POST.get("email"),
            phone=request.POST.get("phone"),
            desc=request.POST.get("desc"),
            date=datetime.today()
        )
    return render(request, "html_home/contact.html")






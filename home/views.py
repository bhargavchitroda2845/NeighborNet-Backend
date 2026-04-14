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
from marketplace.models import BnsModel
from news.models import News
from business.models import Business

def index(request):
    """The landing page now shows the dashboard if no separate frontend is configured."""
    # If the user has a separate frontend (like React), they would use the redirect.
    # For now, we show the internal home dashboard to make the site functional.
    return home(request)

def home(request):
    """Fetches the latest community content for the home dashboard."""
    context = {
        'recent_news': News.objects.filter(status='published').order_by('-published_at')[:3],
        'recent_marketplace': BnsModel.objects.filter(status='published').order_by('-published_at')[:4],
        'recent_businesses': Business.objects.filter(status='published').order_by('-published_at')[:4],
    }
    return render(request, "html_home/home.html", context)


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






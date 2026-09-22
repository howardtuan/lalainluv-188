from django.shortcuts import render
from .models import Banner
from products.models import Product


def home(request):
    products = Product.objects.filter(is_active=True, category__is_active=True).select_related('category')
    return render(request, 'core/home.html', {
        'banners': Banner.objects.filter(is_active=True),
        'new_products': products.filter(is_new=True)[:4],
        'hot_products': products.filter(is_hot=True)[:4],
    })


def about(request):
    return render(request, 'core/about.html')


def notice(request):
    return render(request, 'core/notice.html')

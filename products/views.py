from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Category, Product


def catalog(request, category=None):
    products = Product.objects.filter(is_active=True, category__is_active=True).select_related('category')
    query = request.GET.get('q', '').strip()[:100]
    collection = request.GET.get('collection', '')
    sort = request.GET.get('sort', 'newest')
    if category:
        products = products.filter(category=category)
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if collection == 'new':
        products = products.filter(is_new=True)
    elif collection == 'hot':
        products = products.filter(is_hot=True)
    ordering = {'newest': '-created_at', 'price_asc': 'price', 'price_desc': '-price'}
    products = products.order_by(ordering.get(sort, '-created_at'), 'pk')
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'products/list.html', {
        'page_obj': Paginator(products, 12).get_page(request.GET.get('page')),
        'query': query, 'category': category, 'collection': collection, 'sort': sort,
        'filter_query': params.urlencode(),
        'categories': Category.objects.filter(is_active=True, category_type='hot_sale'),
    })


def product_list(request):
    return catalog(request)


def category_list(request, slug):
    return catalog(request, get_object_or_404(Category, slug=slug, is_active=True))


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related('category'), slug=slug, is_active=True, category__is_active=True)
    related = Product.objects.filter(category=product.category, is_active=True).exclude(pk=product.pk)[:4]
    return render(request, 'products/detail.html', {'product': product, 'related_products': related})

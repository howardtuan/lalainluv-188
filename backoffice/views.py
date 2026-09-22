from functools import wraps
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView, redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from django.views.decorators.http import require_http_methods
from allauth.core import ratelimit
from accounts.services import safe_destination
from core.models import Banner, SiteConfig
from products.models import Product, Category
from orders.models import Order, Wish
from .forms import (StaffLoginForm, ProductForm, ProductImageFormSet, BannerForm,
                    CategoryForm, OrderUpdateForm, WishReplyForm, SiteConfigForm)
from .services import update_order


def staff_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url=reverse('backoffice:login'))
        if not request.user.is_active or not request.user.is_staff:
            raise PermissionDenied
        response = view(request, *args, **kwargs)
        add_never_cache_headers(response)
        return response
    return wrapped


class StaffLoginView(LoginView):
    template_name = 'backoffice/login.html'
    authentication_form = StaffLoginForm

    def get_success_url(self):
        target = safe_destination(self.request, self.get_redirect_url(), '/manage/')
        return target if target.startswith('/manage/') else '/manage/'

    def post(self, request, *args, **kwargs):
        limited = ratelimit.consume_or_429(request, action='staff_login', key=request.POST.get('username', '').casefold())
        return limited if limited is not None else super().post(request, *args, **kwargs)


class StaffLogoutView(LogoutView):
    next_page = '/manage/login/'


def page(request, template, section, **context):
    return render(request, 'backoffice/' + template + '.html', {'management_mode': True, 'active_section': section, **context})


@staff_required
def dashboard(request):
    return page(request, 'dashboard', 'dashboard',
        pending_count=Order.objects.filter(status='pending').count(),
        active_products=Product.objects.filter(is_active=True).count(),
        low_stock=Product.objects.filter(is_active=True, stock__lte=3).count(),
        active_banners=Banner.objects.filter(is_active=True).count(),
        recent_orders=Order.objects.select_related('user')[:6],
        pending_wishes=Wish.objects.filter(status='pending').count())


@staff_required
def products(request):
    query = request.GET.get('q', '')[:200]
    items = Product.objects.select_related('category').filter(name__icontains=query)
    state = request.GET.get('state', '')
    if state == 'active': items = items.filter(is_active=True)
    elif state == 'inactive': items = items.filter(is_active=False)
    elif state == 'low': items = items.filter(is_active=True, stock__lte=3)
    return page(request, 'products', 'products', page_obj=Paginator(items, 12).get_page(request.GET.get('page')), query=query, state=state)


@staff_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def product_edit(request, pk=None):
    product = get_object_or_404(Product.objects.select_for_update(), pk=pk) if pk else Product()
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    images = ProductImageFormSet(request.POST or None, request.FILES or None, instance=product, prefix='images')
    if request.method == 'POST' and form.is_valid() and images.is_valid():
        form.save()
        images.save()
        messages.success(request, '商品已儲存，前台會立即使用新的商品資訊。')
        return redirect('backoffice:products')
    return page(request, 'product_edit', 'products', form=form, images=images, product=product)


@staff_required
def orders(request):
    query, status = request.GET.get('q', '')[:200], request.GET.get('status', '')
    items = Order.objects.select_related('user').filter(Q(order_number__icontains=query) | Q(recipient_name__icontains=query) | Q(customer_email__icontains=query))
    if status in dict(Order.STATUS_CHOICES): items = items.filter(status=status)
    return page(request, 'orders', 'orders', page_obj=Paginator(items, 20).get_page(request.GET.get('page')), query=query, status=status, statuses=Order.STATUS_CHOICES)


@staff_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def order_detail(request, order_number):
    order = get_object_or_404(Order.objects.select_for_update(of=('self',)).select_related('user').prefetch_related('items', 'status_logs__actor'), order_number=order_number)
    form = OrderUpdateForm(request.POST or None, instance=order)
    # ModelForm validation mutates its instance, so validate against a separate object.
    if request.method == 'POST':
        form = OrderUpdateForm(request.POST, instance=Order.objects.get(pk=order.pk))
        if form.is_valid():
            try:
                update_order(order, form.cleaned_data, request.user)
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, '訂單狀態已更新。')
                return redirect('backoffice:order_detail', order_number=order.order_number)
    return page(request, 'order_detail', 'orders', order=order, form=form,
                subtotal=order.total_amount - order.shipping_fee,
                social_accounts=order.user.socialaccount_set.filter(provider__in=['line', 'google']))


@staff_required
def banners(request):
    return page(request, 'banners', 'banners', banners=Banner.objects.all())


@staff_required
@require_http_methods(['GET', 'POST'])
def banner_edit(request, pk=None):
    banner = get_object_or_404(Banner, pk=pk) if pk else None
    form = BannerForm(request.POST or None, request.FILES or None, instance=banner)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '輪播廣告已儲存。排序最前且啟用的圖片會成為首頁首圖。')
        return redirect('backoffice:banners')
    return page(request, 'edit', 'banners', form=form, object=banner, title='編輯輪播廣告' if banner else '新增輪播廣告', back_url=reverse('backoffice:banners'))


@staff_required
def categories(request):
    return page(request, 'categories', 'categories', categories=Category.objects.annotate(product_count=Count('products')))


@staff_required
@require_http_methods(['GET', 'POST'])
def category_edit(request, pk=None):
    category = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '分類已更新。')
        return redirect('backoffice:categories')
    return page(request, 'edit', 'categories', form=form, object=category, title='編輯商品分類' if category else '新增商品分類', back_url=reverse('backoffice:categories'))


@staff_required
def wishes(request):
    return page(request, 'wishes', 'wishes', page_obj=Paginator(Wish.objects.select_related('user'), 20).get_page(request.GET.get('page')))


@staff_required
@require_http_methods(['GET', 'POST'])
def wish_edit(request, pk):
    wish = get_object_or_404(Wish.objects.select_related('user'), pk=pk)
    form = WishReplyForm(request.POST or None, instance=wish)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '回覆已儲存，會員可在許願清單查看。')
        return redirect('backoffice:wishes')
    return page(request, 'wish_edit', 'wishes', form=form, wish=wish)


@staff_required
@require_http_methods(['GET', 'POST'])
def site_settings(request):
    form = SiteConfigForm(request.POST or None, instance=SiteConfig.get_config())
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '網站資訊已更新。')
        return redirect('backoffice:settings')
    return page(request, 'edit', 'settings', form=form, title='網站資訊', back_url=reverse('backoffice:dashboard'))

import json
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import FileResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from products.models import Product
from .models import CartItem, Order, OrderItem, Wish
from .forms import CheckoutForm, WishForm
from .signals import send_order_notification


def get_cart_items(request, create=False):
    if request.user.is_authenticated:
        return CartItem.objects.filter(user=request.user).select_related('product')
    if not request.session.session_key:
        if not create:
            return CartItem.objects.none()
        request.session.save()
    if create:
        request.session['guest_cart_key'] = request.session.session_key
    return CartItem.objects.filter(user__isnull=True, session_key=request.session.session_key).select_related('product')


def totals(items):
    subtotal = sum((i.subtotal for i in items), Decimal('0'))
    shipping = Decimal(settings.SHIPPING_FEE if 0 < subtotal < settings.FREE_SHIPPING_THRESHOLD else 0)
    return {'subtotal': subtotal, 'shipping': shipping, 'total': subtotal + shipping}


def cart_response(request, **extra):
    items = list(get_cart_items(request))
    return JsonResponse({'success': True, 'cart_count': sum(i.quantity for i in items), **totals(items), **extra})


def quantity_input(request, default=1):
    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    value = data.get('quantity', default)
    if isinstance(value, bool) or not str(value).isdigit():
        raise ValueError
    quantity = int(value)
    if not 1 <= quantity <= 99:
        raise ValueError
    return quantity


def cart_view(request):
    items = list(get_cart_items(request))
    return render(request, 'orders/cart.html', {'cart_items': items, **totals(items)})


@require_POST
@transaction.atomic
def cart_add(request, product_id):
    if request.user.is_authenticated:
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
    try:
        quantity = quantity_input(request)
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({'success': False, 'message': '請輸入 1–99 的整數數量。'}, status=400)
    product = get_object_or_404(Product.objects.select_for_update(), pk=product_id, is_active=True, category__is_active=True)
    item = get_cart_items(request, create=True).filter(product=product).first()
    amount = (item.quantity if item else 0) + quantity
    if amount > min(product.stock, 99):
        return JsonResponse({'success': False, 'message': '數量超過可購買庫存，請調整數量。'}, status=400)
    if item:
        item.quantity = amount
        item.save(update_fields=['quantity'])
    else:
        CartItem.objects.create(product=product, quantity=quantity,
            user=request.user if request.user.is_authenticated else None,
            session_key='' if request.user.is_authenticated else request.session.session_key)
    return cart_response(request, message='已把喜歡的好物放進購物車！')


@require_POST
@transaction.atomic
def cart_update(request, item_id):
    if request.user.is_authenticated:
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
    try:
        quantity = quantity_input(request)
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({'success': False, 'message': '請輸入 1–99 的整數數量。'}, status=400)
    item = get_object_or_404(get_cart_items(request).select_for_update(of=('self',)), pk=item_id)
    if not item.product.is_active or quantity > item.product.stock:
        return JsonResponse({'success': False, 'message': '商品庫存不足，請調整數量。'}, status=400)
    item.quantity = quantity
    item.save(update_fields=['quantity'])
    return cart_response(request, item_subtotal=item.subtotal)


@require_POST
@transaction.atomic
def cart_remove(request, item_id):
    if request.user.is_authenticated:
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
    get_object_or_404(get_cart_items(request), pk=item_id).delete()
    return cart_response(request)


@login_required
def checkout(request):
    items = list(get_cart_items(request))
    if not items:
        messages.info(request, '購物車還是空的，先挑選喜歡的商品吧。')
        return redirect('orders:cart')
    profile = request.user.profile
    form = CheckoutForm(request.POST or None, initial={
        'recipient_name': request.user.first_name,
        'recipient_phone': profile.phone, 'recipient_address': profile.address,
    })
    if request.method == 'POST' and form.is_valid():
        if request.POST.get('agree') != 'on':
            form.add_error(None, '請先閱讀並同意購物須知。')
            return render(request, 'orders/checkout.html', {'form': form, 'cart_items': items, **totals(items)})
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            items = list(get_cart_items(request).select_for_update(of=('self',)))
            locked = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[i.product_id for i in items]).order_by('pk')}
            invalid = not items
            for item in items:
                item.product = locked[item.product_id]
                if not item.product.is_active or not item.product.category.is_active or item.quantity > item.product.stock:
                    invalid = True
            if invalid:
                messages.error(request, '部分商品庫存已變動，請確認購物車後再送出。')
                return redirect('orders:cart')
            amounts = totals(items)
            order = form.save(commit=False)
            order.user = request.user
            order.customer_email = request.user.email
            order.total_amount = amounts['total']
            order.shipping_fee = amounts['shipping']
            order.save()
            for item in items:
                OrderItem.objects.create(order=order, product=item.product, product_name=item.product.name,
                                         quantity=item.quantity, price=item.product.price)
                item.product.stock -= item.quantity
                item.product.save(update_fields=['stock', 'updated_at'])
            CartItem.objects.filter(pk__in=[i.pk for i in items]).delete()
            transaction.on_commit(lambda: send_order_notification(order.pk))
        messages.success(request, '訂單已送至管理員後台！我們會人工確認商品並聯絡你；網站不會自動扣款。')
        return redirect('orders:order_detail', order_number=order.order_number)
    return render(request, 'orders/checkout.html', {'form': form, 'cart_items': items, **totals(items)})


@login_required
def order_list(request):
    return render(request, 'orders/order_list.html', {'orders': Order.objects.filter(user=request.user).prefetch_related('items')})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items'), order_number=order_number, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


def wish_list(request):
    kind = request.GET.get('type', '')
    wishes = Wish.objects.filter(user=request.user) if request.user.is_authenticated else Wish.objects.none()
    if kind in dict(Wish.WISH_TYPES):
        wishes = wishes.filter(wish_type=kind)
    return render(request, 'orders/wish_list.html', {'wishes': wishes, 'current_type': kind})


@login_required
def wish_create(request):
    kind = request.GET.get('type', 'product_wish')
    if kind not in dict(Wish.WISH_TYPES):
        kind = 'product_wish'
    form = WishForm(request.POST or None, request.FILES or None, initial={'wish_type': kind})
    if request.method == 'POST' and form.is_valid():
        wish = form.save(commit=False)
        wish.user = request.user
        wish.save()
        messages.success(request, '收到你的願望了！進度與回覆會顯示在許願清單。')
        return redirect('orders:wish_list')
    return render(request, 'orders/wish_create.html', {'form': form})


@login_required
def wish_image(request, pk):
    wishes = Wish.objects.all() if request.user.is_staff else Wish.objects.filter(user=request.user)
    wish = get_object_or_404(wishes, pk=pk)
    if not wish.reference_image:
        raise Http404
    response = FileResponse(wish.reference_image.open('rb'))
    response['Cache-Control'] = 'private, no-store'
    return response
